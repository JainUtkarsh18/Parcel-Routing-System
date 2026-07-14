import json
from functools import lru_cache
from pathlib import Path
from .models import RoutingConfig

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "routing_rules.json"


@lru_cache(maxsize=1)
def load_routing_config(config_path: str | None = None) -> RoutingConfig:
    """Load and validate routing configuration.

    The app fails fast when the configuration is unsafe. This prevents incorrect
    business rules from silently routing real parcels to the wrong department.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    with path.open("r", encoding="utf-8") as file:
        raw_config = json.load(file)
    return RoutingConfig.model_validate(raw_config)


def clear_config_cache() -> None:
    load_routing_config.cache_clear()
