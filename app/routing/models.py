from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class Parcel(BaseModel):
    weight: float = Field(..., gt=0, description="Parcel weight in kilograms")
    value: float = Field(..., ge=0, description="Parcel value in euros")
    destination_country: str = Field(..., min_length=2, description="Destination country")
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("destination_country")
    @classmethod
    def clean_country(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Destination country is required")
        return cleaned


class WeightRule(BaseModel):
    max_weight: Optional[float] = Field(default=None, description="Inclusive maximum weight. Null means no upper limit.")
    department: str = Field(..., min_length=1)

    @field_validator("max_weight")
    @classmethod
    def max_weight_must_be_positive(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value <= 0:
            raise ValueError("max_weight must be positive or null")
        return value


class CustomsReviewConfig(BaseModel):
    enabled: bool = False
    eu_countries: List[str] = Field(default_factory=list)


class RoutingConfig(BaseModel):
    rule_version: str = Field(..., min_length=1)
    insurance_threshold: float = Field(..., gt=0)
    weight_rules: List[WeightRule] = Field(..., min_length=1)
    customs_review: CustomsReviewConfig = Field(default_factory=CustomsReviewConfig)

    @field_validator("weight_rules")
    @classmethod
    def validate_weight_rules(cls, rules: List[WeightRule]) -> List[WeightRule]:
        unlimited_rules = [rule for rule in rules if rule.max_weight is None]
        if len(unlimited_rules) != 1:
            raise ValueError("Exactly one unlimited weight rule with max_weight=null is required")
        if rules[-1].max_weight is not None:
            raise ValueError("The unlimited weight rule must be the last rule")

        previous_limit = 0.0
        for rule in rules[:-1]:
            if rule.max_weight is None:
                raise ValueError("Only the last weight rule can have max_weight=null")
            if rule.max_weight <= previous_limit:
                raise ValueError("Weight rules must be ordered by increasing max_weight")
            previous_limit = rule.max_weight

        departments = [rule.department.strip() for rule in rules]
        if any(not department for department in departments):
            raise ValueError("Department names cannot be blank")
        return rules


class RoutingDecision(BaseModel):
    department: str
    insurance_required: bool
    approvals_required: List[str]
    applied_rules: List[str]
    rule_version: str


class BatchRoutingResult(BaseModel):
    total_records: int
    successfully_routed: int
    failed_validation: int
    results: List[Dict[str, Any]]
    errors: List[Dict[str, Any]]
