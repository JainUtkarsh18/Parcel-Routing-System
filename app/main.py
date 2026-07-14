import json
import logging
from typing import Any, Dict, List

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .routing.config_loader import load_routing_config
from .routing.models import BatchRoutingResult, Parcel
from .routing.router import ParcelRouter
from .security import SecurityHeadersMiddleware, SimpleRateLimitMiddleware

MAX_UPLOAD_BYTES = 5 * 1024 * 1024

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("parcel_routing")

app = FastAPI(
    title="Parcel Routing System",
    description="Routes parcels using configurable business rules.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SimpleRateLimitMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


def get_router() -> ParcelRouter:
    config = load_routing_config()
    return ParcelRouter(config)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/health")
def health() -> Dict[str, str]:
    config = load_routing_config()
    return {"status": "ok", "rule_version": config.rule_version}


@app.post("/api/route")
def route_single_parcel(parcel: Parcel) -> Dict[str, Any]:
    decision = get_router().route(parcel)
    return {
        "parcel": parcel.model_dump(),
        "decision": decision.model_dump(),
    }


@app.post("/api/route/batch", response_model=BatchRoutingResult)
async def route_batch(file: UploadFile = File(...)) -> BatchRoutingResult:
    if file.content_type not in {"application/json", "text/json"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JSON files are supported.",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File is too large. Maximum supported size is 5 MB.",
        )

    try:
        records = json.loads(content.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON file: {exc.msg}",
        ) from exc

    if not isinstance(records, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch file must contain a JSON array of parcels.",
        )

    router = get_router()
    results: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        try:
            parcel = Parcel.model_validate(record)
            decision = router.route(parcel)
            results.append(
                {
                    "row": index,
                    "parcel": parcel.model_dump(),
                    "decision": decision.model_dump(),
                }
            )
        except ValidationError as exc:
            errors.append(
                {
                    "row": index,
                    "input": record,
                    "errors": exc.errors(),
                }
            )

    return BatchRoutingResult(
        total_records=len(records),
        successfully_routed=len(results),
        failed_validation=len(errors),
        results=results,
        errors=errors,
    )
