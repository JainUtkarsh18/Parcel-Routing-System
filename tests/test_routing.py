import pytest
from pydantic import ValidationError

from app.routing.models import Parcel, RoutingConfig
from app.routing.router import ParcelRouter


@pytest.fixture
def routing_config():
    return RoutingConfig.model_validate(
        {
            "rule_version": "test-v1",
            "insurance_threshold": 1000,
            "weight_rules": [
                {"max_weight": 1, "department": "Mail Department"},
                {"max_weight": 10, "department": "Regular Department"},
                {"max_weight": None, "department": "Heavy Department"},
            ],
            "customs_review": {"enabled": False, "eu_countries": ["Germany", "France"]},
        }
    )


@pytest.fixture
def router(routing_config):
    return ParcelRouter(routing_config)


@pytest.mark.parametrize(
    "weight, expected_department",
    [
        (0.5, "Mail Department"),
        (1.0, "Mail Department"),
        (1.1, "Regular Department"),
        (10.0, "Regular Department"),
        (10.1, "Heavy Department"),
    ],
)
def test_weight_boundaries(router, weight, expected_department):
    parcel = Parcel(weight=weight, value=100, destination_country="Germany")
    decision = router.route(parcel)
    assert decision.department == expected_department


def test_value_equal_to_threshold_does_not_require_insurance(router):
    parcel = Parcel(weight=5, value=1000, destination_country="Germany")
    decision = router.route(parcel)
    assert decision.insurance_required is False
    assert "Insurance Approval" not in decision.approvals_required


def test_value_above_threshold_requires_insurance(router):
    parcel = Parcel(weight=5, value=1000.01, destination_country="Germany")
    decision = router.route(parcel)
    assert decision.insurance_required is True
    assert "Insurance Approval" in decision.approvals_required


@pytest.mark.parametrize(
    "payload",
    [
        {"weight": -1, "value": 100, "destination_country": "Germany"},
        {"weight": 0, "value": 100, "destination_country": "Germany"},
        {"weight": 1, "value": -5, "destination_country": "Germany"},
        {"weight": 1, "value": 100, "destination_country": ""},
    ],
)
def test_invalid_parcel_data_is_rejected(payload):
    with pytest.raises(ValidationError):
        Parcel.model_validate(payload)


def test_invalid_config_rejects_missing_unlimited_rule():
    with pytest.raises(ValidationError):
        RoutingConfig.model_validate(
            {
                "rule_version": "bad-config",
                "insurance_threshold": 1000,
                "weight_rules": [
                    {"max_weight": 1, "department": "Mail Department"},
                    {"max_weight": 10, "department": "Regular Department"},
                ],
            }
        )


def test_invalid_config_rejects_unordered_rules():
    with pytest.raises(ValidationError):
        RoutingConfig.model_validate(
            {
                "rule_version": "bad-config",
                "insurance_threshold": 1000,
                "weight_rules": [
                    {"max_weight": 10, "department": "Regular Department"},
                    {"max_weight": 1, "department": "Mail Department"},
                    {"max_weight": None, "department": "Heavy Department"},
                ],
            }
        )


def test_customs_review_can_be_added_safely():
    config = RoutingConfig.model_validate(
        {
            "rule_version": "test-v2",
            "insurance_threshold": 1000,
            "weight_rules": [
                {"max_weight": 1, "department": "Mail Department"},
                {"max_weight": 10, "department": "Regular Department"},
                {"max_weight": None, "department": "Heavy Department"},
            ],
            "customs_review": {"enabled": True, "eu_countries": ["Germany", "France"]},
        }
    )
    router = ParcelRouter(config)

    eu_parcel = Parcel(weight=2, value=200, destination_country="Germany")
    non_eu_parcel = Parcel(weight=2, value=200, destination_country="India")

    assert "Customs Review" not in router.route(eu_parcel).approvals_required
    assert "Customs Review" in router.route(non_eu_parcel).approvals_required
