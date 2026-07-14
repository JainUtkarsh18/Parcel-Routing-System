import logging
from .models import Parcel, RoutingConfig, RoutingDecision

logger = logging.getLogger("parcel_routing")


class ParcelRouter:
    """Routes parcels using validated business configuration."""

    def __init__(self, config: RoutingConfig):
        self.config = config

    def route(self, parcel: Parcel) -> RoutingDecision:
        applied_rules: list[str] = []
        approvals_required: list[str] = []

        department = self._department_by_weight(parcel.weight, applied_rules)

        insurance_required = parcel.value > self.config.insurance_threshold
        if insurance_required:
            approvals_required.append("Insurance Approval")
            applied_rules.append(
                f"value>{self.config.insurance_threshold}: Insurance Approval required"
            )
        else:
            applied_rules.append(
                f"value<={self.config.insurance_threshold}: No insurance approval required"
            )

        if self.config.customs_review.enabled:
            eu_countries = {country.lower() for country in self.config.customs_review.eu_countries}
            if parcel.destination_country.lower() not in eu_countries:
                approvals_required.append("Customs Review")
                applied_rules.append("non_eu_destination: Customs Review required")

        decision = RoutingDecision(
            department=department,
            insurance_required=insurance_required,
            approvals_required=approvals_required,
            applied_rules=applied_rules,
            rule_version=self.config.rule_version,
        )

        logger.info(
            "parcel_routed",
            extra={
                "weight": parcel.weight,
                "value": parcel.value,
                "destination_country": parcel.destination_country,
                "department": decision.department,
                "approvals_required": decision.approvals_required,
                "rule_version": decision.rule_version,
            },
        )
        return decision

    def _department_by_weight(self, weight: float, applied_rules: list[str]) -> str:
        for rule in self.config.weight_rules:
            if rule.max_weight is None:
                applied_rules.append(f"weight>{self.config.weight_rules[-2].max_weight}: {rule.department}")
                return rule.department
            if weight <= rule.max_weight:
                applied_rules.append(f"weight<={rule.max_weight}: {rule.department}")
                return rule.department
        raise RuntimeError("No routing rule matched. Check routing configuration.")
