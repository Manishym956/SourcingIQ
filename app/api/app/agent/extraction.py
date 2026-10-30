"""Schema gate for model output. Extra authority fields are dropped, never applied."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Protocol

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

ALLOWED_FIELDS = {
    "material",
    "specification",
    "quantity",
    "unit",
    "delivery_location",
    "needed_by",
    "budget_amount",
    "currency",
}
REQUIRED_FIELDS = (
    "material",
    "specification",
    "quantity",
    "unit",
    "delivery_location",
    "needed_by",
)


class ExtractedFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: str | None = None
    specification: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    delivery_location: str | None = None
    needed_by: date | None = None
    budget_amount: Decimal | None = None
    currency: str | None = None

    @field_validator("material", "specification", "delivery_location", "unit", "currency")
    @classmethod
    def blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("quantity", "budget_amount")
    @classmethod
    def positive_or_none(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if value <= 0:
            raise ValueError("Must be greater than zero.")
        return value


class ExtractionResult(BaseModel):
    status: str
    fields: ExtractedFields
    ignored_fields: list[str]
    missing_fields: list[str]
    reason: str | None


class RfqExtractor(Protocol):
    def extract(self, text: str) -> dict[str, object]:
        """Return a raw field dict. It is not trusted until accept_model_output."""


class PatternExtractor:
    """Local stand-in used when no model provider is configured."""

    def extract(self, text: str) -> dict[str, object]:
        fields: dict[str, object] = {}
        quantity = re.search(r"(\d+(?:\.\d+)?)\s*tonne", text, flags=re.IGNORECASE)
        if quantity:
            fields["quantity"] = quantity.group(1)
            fields["unit"] = "tonne"
        specification = re.search(r"\bFe\s*([0-9]+[A-Za-z]*)\b", text, flags=re.IGNORECASE)
        if specification:
            fields["specification"] = f"Fe {specification.group(1).upper()}"
        if re.search(r"\bTMT\s+steel\b", text, flags=re.IGNORECASE):
            fields["material"] = "TMT steel"
        location = re.search(
            r"(?:deliver(?:y)?(?:\s+location)?(?:\s+to)?|for)\s+([A-Z][A-Za-z]+(?:,\s*[A-Za-z]+)?)",
            text,
        )
        if location:
            fields["delivery_location"] = location.group(1).strip().rstrip(".")
        needed = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        if needed:
            fields["needed_by"] = needed.group(1)
        budget = re.search(
            r"budget\s+(?:of\s+)?(?:INR\s*)?(\d+(?:\.\d+)?)\s*(?:INR)?",
            text,
            flags=re.IGNORECASE,
        )
        if budget:
            fields["budget_amount"] = budget.group(1)
            fields["currency"] = "INR"
        return fields


def accept_model_output(payload: dict[str, object]) -> ExtractionResult:
    """Validate a model dict. Disallowed keys cannot change eligibility, money, or approval."""
    ignored = sorted(key for key in payload if key not in ALLOWED_FIELDS)
    cleaned: dict[str, object] = {}
    for key in ALLOWED_FIELDS:
        if key not in payload or payload[key] in ("", None):
            continue
        cleaned[key] = payload[key]
    try:
        fields = ExtractedFields.model_validate(cleaned)
    except (ValidationError, InvalidOperation):
        return ExtractionResult(
            status="abstained",
            fields=ExtractedFields(),
            ignored_fields=ignored,
            missing_fields=list(REQUIRED_FIELDS),
            reason="The extracted fields did not match the RFQ schema.",
        )
    missing = [name for name in REQUIRED_FIELDS if getattr(fields, name) is None]
    if fields.unit not in (None, "tonne") or fields.currency not in (None, "INR"):
        return ExtractionResult(
            status="abstained",
            fields=ExtractedFields(),
            ignored_fields=ignored,
            missing_fields=missing or list(REQUIRED_FIELDS),
            reason="Only tonne and INR can be extracted in this demo.",
        )
    if missing:
        return ExtractionResult(
            status="abstained",
            fields=fields,
            ignored_fields=ignored,
            missing_fields=missing,
            reason="Required fields are missing, so nothing was invented.",
        )
    return ExtractionResult(
        status="complete",
        fields=fields,
        ignored_fields=ignored,
        missing_fields=[],
        reason=None,
    )
