# Parcel Routing System

A production-style technical assessment project for routing parcels to departments based on configurable business rules.

## Features

- Manual parcel entry through a simple web interface
- Batch JSON upload
- Configurable routing rules
- Insurance approval rule for high-value parcels
- Optional customs review rule
- Validation of parcel data and configuration
- Automated tests for boundary cases and regressions
- Basic public internet security controls
- Structured routing decisions with applied rule explanations
- Health endpoint for monitoring

## Tech Stack

- Python 3.12
- FastAPI
- Pydantic
- Pytest
- HTML, CSS, JavaScript
- JSON configuration
- Docker support

## How to Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

## How to Run Tests

```bash
pytest
```

## How to Run with Docker

```bash
docker build -t parcel-routing-system .
docker run -p 8000:8000 parcel-routing-system
```

## Routing Rules

Current default rules:

| Condition | Outcome |
|---|---|
| Weight up to 1 kg | Mail Department |
| Weight up to 10 kg | Regular Department |
| Weight over 10 kg | Heavy Department |
| Value greater than €1,000 | Insurance Approval required |

The system uses inclusive weight boundaries. A parcel weighing exactly 1 kg goes to Mail Department. A parcel weighing exactly 10 kg goes to Regular Department.

## Configuration

Rules are stored in:

```text
app/config/routing_rules.json
```

Example:

```json
{
  "rule_version": "v1.0",
  "insurance_threshold": 1000,
  "weight_rules": [
    {"max_weight": 1, "department": "Mail Department"},
    {"max_weight": 10, "department": "Regular Department"},
    {"max_weight": null, "department": "Heavy Department"}
  ]
}
```

The configuration is validated at startup. Unsafe configuration is rejected, such as:

- Missing unlimited weight rule
- More than one unlimited weight rule
- Weight rules in the wrong order
- Negative thresholds
- Blank department names

This protects the business from accidentally routing large volumes of parcels incorrectly.

## Batch Upload Format

The app supports JSON batch upload.

Reason for choosing JSON:

JSON is simpler than XML, easy to validate, widely used in APIs, and readable enough for operators and developers.

Example:

```json
[
  {"weight": 0.8, "value": 100, "destination_country": "Germany"},
  {"weight": 7.5, "value": 1200, "destination_country": "France"},
  {"weight": 15, "value": 600, "destination_country": "India"}
]
```

## Architecture Decisions

The system separates responsibilities clearly:

- `models.py` defines validated parcel, rule, config, and decision models.
- `config_loader.py` loads and validates routing configuration.
- `router.py` contains routing logic.
- `main.py` exposes API and UI endpoints.
- `security.py` adds basic security middleware.
- `tests/` protects business behavior from regressions.

The router does not depend on the UI. This means the same routing engine can be used by a web form, batch upload, another internal API, or a future message queue.

## How to Extend the System with a New Rule

Example new rule:

```text
Non-EU parcels require Customs Review.
```

The project already includes an optional customs review configuration.

To enable it, update `app/config/routing_rules.json`:

```json
"customs_review": {
  "enabled": true,
  "eu_countries": ["Germany", "France", "Italy", "Spain"]
}
```

Then run:

```bash
pytest
```

The test `test_customs_review_can_be_added_safely` shows how the new rule is introduced without breaking old routing behavior.

## Feature Branch to Merge Example

Feature: Add customs review for non-EU parcels

```bash
git checkout -b feature/customs-review-rule
```

Development steps:

1. Add the customs review configuration.
2. Add routing logic for non-EU parcels.
3. Add tests for EU and non-EU destinations.
4. Run the full test suite.
5. Open a pull request.
6. Review checklist:
   - Tests pass
   - Rule documented
   - Config validation still passes
   - Existing weight routing is not affected
7. Merge to main.

## Testing Strategy

The tests cover:

- Weight boundaries: 1 kg and 10 kg
- Insurance threshold boundary: €1,000
- Invalid parcel data
- Invalid configuration
- Safe introduction of a new customs review rule
- API endpoint behavior
- Batch upload with both valid and invalid rows

Boundary tests are important because routing bugs often happen at exact cut-off values.

## Correctness Beyond Automated Tests

Beyond automated tests, I would validate correctness through:

- Manual testing with business-provided examples
- Review of routing outcomes for historical parcel data
- Code review before merging rule changes
- Staging deployment before production
- Audit logs for routing decisions
- Monitoring department distribution after every rule change

## Monitoring and Reliability

Implemented:

- `/health` endpoint
- Application logging
- Routing decisions include rule version and applied rules
- Validation errors are reported row by row in batch uploads

Production additions:

- Centralized logs using ELK, Datadog, Grafana Loki, or CloudWatch
- Metrics such as parcels routed per department
- Alert if validation failures rise suddenly
- Alert if unusual routing patterns appear
- Error tracking using Sentry or a similar tool
- Audit trail with parcel ID, rule version, decision, and timestamp

## Security Measures

Implemented:

- Pydantic input validation
- JSON-only batch upload
- Upload size limit of 5 MB
- Basic rate limiting
- CORS restriction
- Security headers
- No secrets in source code
- Safe error handling for invalid files

Additional production measures:

- Authentication for operators
- Role-based access control
- HTTPS only
- CSRF protection if using cookie-based authentication
- Web Application Firewall
- Dependency scanning
- Container image scanning
- Secrets manager
- Audit logging
- API gateway rate limits

## AI Usage Documentation

AI was used in two areas.

### 1. Test Case Generation

Prompt used:

```text
Generate boundary and negative test cases for a parcel routing system where parcels up to 1 kg go to Mail, up to 10 kg go to Regular, over 10 kg go to Heavy, and value over €1,000 requires insurance approval.
```

What was changed:

I reviewed the generated cases, removed duplicates, and added tests for invalid configuration and the optional customs review rule.

### 2. README and Architecture Review

Prompt used:

```text
Review the architecture of a FastAPI parcel routing system that uses configurable routing rules, batch JSON upload, tests, logging, and basic security. Suggest what should be explained in the README for a technical assessment.
```

What was changed:

I rewrote the README in my own words, added concrete project details, and included trade-offs, extension guidance, monitoring, and security reasoning.

### Limitations of AI

AI is useful for drafts and edge-case suggestions, but it can miss business meaning. For this project, I treated AI output as a starting point and checked it against the assessment requirements, especially the boundary rules and security risks.

## Trade-offs

- JSON was chosen over XML because it is simpler and better suited for web APIs.
- In-memory rate limiting is acceptable for the assessment, but production should use Redis, API Gateway, or WAF-based controls.
- The frontend is intentionally simple because operator clarity is more important than visual complexity.
- The configuration is file-based for simplicity. In production, a controlled admin workflow with approval and rollback would be safer.

## Debugging Preparation

Likely bug pattern:

```python
def route(weight):
    if weight < 1:
        return "Mail Department"
    elif weight < 10:
        return "Regular Department"
    return "Heavy Department"
```

Issue:

The requirements say up to 1 kg and up to 10 kg, so comparisons must be inclusive.

Correct logic:

```python
def route(weight):
    if weight <= 1:
        return "Mail Department"
    elif weight <= 10:
        return "Regular Department"
    return "Heavy Department"
```

---

##  License

This project is licensed under the MIT License.

---

I am open to more collaborations and recommendations on this notebook.
