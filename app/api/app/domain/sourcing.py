"""Deterministic money, eligibility, and ranking. No model calls."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

MONEY_PLACES = Decimal("0.01")
CALCULATION_VERSION = "landed-cost-v1"


def quantize_money(value: Decimal) -> Decimal:
    """Round half up to 0.01. Apply to each component and to the final total."""
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def money_text(value: Decimal) -> str:
    return format(quantize_money(value), "f")


@dataclass(frozen=True)
class RfqSpec:
    material: str
    specification: str
    quantity: Decimal
    unit: str
    currency: str
    needed_by: date


@dataclass(frozen=True)
class CatalogueOffer:
    supplier_id: str
    supplier_name: str
    quotation_id: str
    material: str
    specification: str
    available_quantity: Decimal
    capability_unit: str
    lead_time_days: int
    unit_price: Decimal
    currency: str
    quote_quantity: Decimal
    quote_unit: str
    freight_amount: Decimal | None
    tax_amount: Decimal | None
    discount_amount: Decimal | None
    tax_included: bool | None
    valid_until: date | None


@dataclass
class OfferResult:
    supplier_id: str
    supplier_name: str
    quotation_id: str
    eligible: bool
    exclusion_reasons: list[str]
    landed_cost: Decimal | None
    currency: str
    lead_time_days: int | None
    breakdown: dict[str, str | bool] | None
    ranking_reasons: list[str]


def evaluate_offer(rfq: RfqSpec, offer: CatalogueOffer, *, as_of: date) -> OfferResult:
    reasons: list[str] = []
    if (
        offer.material.casefold() != rfq.material.casefold()
        or offer.specification.casefold() != rfq.specification.casefold()
    ):
        reasons.append(
            "Supplier excluded: specification is "
            f"{offer.material} {offer.specification}, requested {rfq.material} {rfq.specification}."
        )
    if offer.capability_unit != rfq.unit or offer.quote_unit != rfq.unit:
        reasons.append(f"Supplier excluded: unit is {offer.quote_unit}, requested {rfq.unit}.")
    elif offer.available_quantity < rfq.quantity:
        reasons.append(
            "Supplier excluded: available quantity is "
            f"{_qty(offer.available_quantity)} {offer.capability_unit}, "
            f"requested {_qty(rfq.quantity)} {rfq.unit}."
        )
    if offer.currency != rfq.currency:
        if not offer.currency:
            reasons.append("Price comparison unavailable: supplier currency is missing.")
        else:
            reasons.append(
                f"Supplier excluded: currency is {offer.currency}, requested {rfq.currency}."
            )
    arrival = as_of + timedelta(days=offer.lead_time_days)
    if arrival > rfq.needed_by:
        late_days = (arrival - rfq.needed_by).days
        day_word = "day" if late_days == 1 else "days"
        reasons.append(
            "Supplier excluded: delivery is "
            f"{late_days} {day_word} later than the requested deadline."
        )
    if offer.valid_until is not None and offer.valid_until < as_of:
        reasons.append("Supplier excluded: offer is past its validity date.")

    cost_blocked = offer.currency != rfq.currency or offer.quote_unit != rfq.unit
    breakdown, landed = (None, None) if cost_blocked else _landed_cost(offer, rfq.quantity)
    if not cost_blocked and landed is None:
        reasons.append(_missing_cost_reason(offer))
    elif landed is not None and landed < 0:
        reasons.append("Supplier excluded: discount exceeds the calculated cost.")
        breakdown = None
        landed = None

    evidence: list[str] = []
    if not reasons:
        evidence = [
            f"Specification matches {rfq.material} {rfq.specification}",
            (
                f"Available quantity {_qty(offer.available_quantity)} {offer.capability_unit} "
                f"covers {_qty(rfq.quantity)} {rfq.unit}"
            ),
            f"Delivery in {offer.lead_time_days} days meets {rfq.needed_by.isoformat()}",
        ]
    return OfferResult(
        supplier_id=offer.supplier_id,
        supplier_name=offer.supplier_name,
        quotation_id=offer.quotation_id,
        eligible=not reasons,
        exclusion_reasons=reasons,
        landed_cost=landed,
        currency=rfq.currency,
        lead_time_days=offer.lead_time_days,
        breakdown=breakdown if landed is not None else None,
        ranking_reasons=evidence,
    )


def rank_offers(results: list[OfferResult]) -> list[OfferResult]:
    eligible = [item for item in results if item.eligible and item.landed_cost is not None]
    ineligible = [item for item in results if item not in eligible]
    eligible.sort(key=lambda item: (item.landed_cost, item.lead_time_days, item.supplier_name))
    for index, item in enumerate(eligible):
        if index == 0:
            item.ranking_reasons = [
                *item.ranking_reasons,
                "Lowest landed cost among eligible offers",
            ]
        else:
            item.ranking_reasons = [
                *item.ranking_reasons,
                "Higher landed cost than the leading eligible offer",
            ]
    for item in ineligible:
        item.ranking_reasons = []
        item.eligible = False
    ineligible.sort(key=lambda item: item.supplier_name)
    return eligible + ineligible


def _landed_cost(
    offer: CatalogueOffer, quantity: Decimal
) -> tuple[dict[str, str | bool] | None, Decimal | None]:
    if offer.freight_amount is None or offer.discount_amount is None or offer.tax_included is None:
        return None, None
    if offer.tax_included is False and offer.tax_amount is None:
        return None, None
    subtotal = quantize_money(offer.unit_price * quantity)
    freight = quantize_money(offer.freight_amount)
    discount = quantize_money(offer.discount_amount)
    tax = Decimal("0.00") if offer.tax_included else quantize_money(offer.tax_amount or Decimal(0))
    landed = quantize_money(subtotal + freight + tax - discount)
    breakdown: dict[str, str | bool] = {
        "material_subtotal": money_text(subtotal),
        "freight": money_text(freight),
        "tax": money_text(tax),
        "discount": money_text(discount),
        "landed_cost": money_text(landed),
        "tax_included": offer.tax_included,
    }
    return breakdown, landed


def _missing_cost_reason(offer: CatalogueOffer) -> str:
    if offer.tax_included is None or (offer.tax_included is False and offer.tax_amount is None):
        return "Supplier excluded: tax treatment is unknown."
    if offer.freight_amount is None:
        return "Price comparison unavailable: freight is missing."
    if offer.discount_amount is None:
        return "Price comparison unavailable: discount is missing."
    return "Price comparison unavailable: cost inputs are incomplete."


def _qty(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"
