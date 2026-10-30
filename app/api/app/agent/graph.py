"""LangGraph adapter. Nodes call the deterministic domain and cannot override it."""

from datetime import date
from decimal import Decimal
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.domain.sourcing import (
    CatalogueOffer,
    OfferResult,
    RfqSpec,
    evaluate_offer,
    rank_offers,
)

ORCHESTRATOR = "langgraph"
GRAPH_STEPS = (
    "validate_rfq",
    "search_suppliers",
    "evaluate_eligibility",
    "calculate_landed_cost",
    "rank_offers",
)


class ComparisonState(TypedDict):
    spec: dict[str, str]
    offers: list[dict[str, str | None]]
    as_of: str
    evaluated: list[dict[str, object]]
    steps: list[str]


def _spec(state: ComparisonState) -> RfqSpec:
    raw = state["spec"]
    return RfqSpec(
        material=raw["material"],
        specification=raw["specification"],
        quantity=Decimal(raw["quantity"]),
        unit=raw["unit"],
        currency=raw["currency"],
        needed_by=date.fromisoformat(raw["needed_by"]),
    )


def _offer(raw: dict[str, str | None]) -> CatalogueOffer:
    def money(key: str) -> Decimal | None:
        value = raw.get(key)
        if value is None:
            return None
        return Decimal(value)

    valid_until = raw.get("valid_until")
    tax_included = raw.get("tax_included")
    return CatalogueOffer(
        supplier_id=str(raw["supplier_id"]),
        supplier_name=str(raw["supplier_name"]),
        quotation_id=str(raw["quotation_id"]),
        material=str(raw["material"]),
        specification=str(raw["specification"]),
        available_quantity=Decimal(str(raw["available_quantity"])),
        capability_unit=str(raw["capability_unit"]),
        lead_time_days=int(str(raw["lead_time_days"])),
        unit_price=Decimal(str(raw["unit_price"])),
        currency=str(raw["currency"]),
        quote_quantity=Decimal(str(raw["quote_quantity"])),
        quote_unit=str(raw["quote_unit"]),
        freight_amount=money("freight_amount"),
        tax_amount=money("tax_amount"),
        discount_amount=money("discount_amount"),
        tax_included=None if tax_included is None else tax_included == "true",
        valid_until=None if valid_until is None else date.fromisoformat(valid_until),
    )


def _result_dict(result: OfferResult) -> dict[str, object]:
    return {
        "supplier_id": result.supplier_id,
        "supplier_name": result.supplier_name,
        "quotation_id": result.quotation_id,
        "eligible": result.eligible,
        "exclusion_reasons": list(result.exclusion_reasons),
        "landed_cost": None if result.landed_cost is None else format(result.landed_cost, "f"),
        "currency": result.currency,
        "lead_time_days": result.lead_time_days,
        "breakdown": result.breakdown,
        "ranking_reasons": list(result.ranking_reasons),
    }


def _mark(state: ComparisonState, step: str) -> list[str]:
    return [*state["steps"], step]


def validate_rfq(state: ComparisonState) -> dict[str, object]:
    spec = state["spec"]
    required = ("material", "specification", "quantity", "unit", "currency", "needed_by")
    if any(not spec.get(name) for name in required):
        raise ValueError("RFQ is missing a required field.")
    if spec["unit"] != "tonne" or spec["currency"] != "INR":
        raise ValueError("Only tonne and INR are supported.")
    if Decimal(spec["quantity"]) <= 0:
        raise ValueError("Quantity must be greater than zero.")
    return {"steps": _mark(state, "validate_rfq")}


def search_suppliers(state: ComparisonState) -> dict[str, object]:
    return {"steps": _mark(state, "search_suppliers")}


def evaluate_eligibility(state: ComparisonState) -> dict[str, object]:
    spec = _spec(state)
    as_of = date.fromisoformat(state["as_of"])
    evaluated = [
        _result_dict(evaluate_offer(spec, _offer(offer), as_of=as_of)) for offer in state["offers"]
    ]
    return {"evaluated": evaluated, "steps": _mark(state, "evaluate_eligibility")}


def calculate_landed_cost(state: ComparisonState) -> dict[str, object]:
    """Landed cost is already on each evaluation. This step does not recompute it."""
    return {"steps": _mark(state, "calculate_landed_cost")}


def rank_node(state: ComparisonState) -> dict[str, object]:
    results = [_result_from_dict(item) for item in state["evaluated"]]
    ranked = rank_offers(results)
    return {
        "evaluated": [_result_dict(item) for item in ranked],
        "steps": _mark(state, "rank_offers"),
    }


def _result_from_dict(raw: dict[str, object]) -> OfferResult:
    landed = raw["landed_cost"]
    lead = raw["lead_time_days"]
    return OfferResult(
        supplier_id=str(raw["supplier_id"]),
        supplier_name=str(raw["supplier_name"]),
        quotation_id=str(raw["quotation_id"]),
        eligible=bool(raw["eligible"]),
        exclusion_reasons=list(raw["exclusion_reasons"]),  # type: ignore[arg-type]
        landed_cost=None if landed is None else Decimal(str(landed)),
        currency=str(raw["currency"]),
        lead_time_days=None if lead is None else int(str(lead)),
        breakdown=raw["breakdown"],  # type: ignore[arg-type]
        ranking_reasons=list(raw["ranking_reasons"]),  # type: ignore[arg-type]
    )


def _compile():
    graph = StateGraph(ComparisonState)
    graph.add_node("validate_rfq", validate_rfq)
    graph.add_node("search_suppliers", search_suppliers)
    graph.add_node("evaluate_eligibility", evaluate_eligibility)
    graph.add_node("calculate_landed_cost", calculate_landed_cost)
    graph.add_node("rank_offers", rank_node)
    graph.add_edge(START, "validate_rfq")
    graph.add_edge("validate_rfq", "search_suppliers")
    graph.add_edge("search_suppliers", "evaluate_eligibility")
    graph.add_edge("evaluate_eligibility", "calculate_landed_cost")
    graph.add_edge("calculate_landed_cost", "rank_offers")
    graph.add_edge("rank_offers", END)
    return graph.compile()


_GRAPH = None


def rank_catalogue(
    spec: RfqSpec, offers: list[CatalogueOffer], *, as_of: date
) -> tuple[list[OfferResult], list[str]]:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = _compile()
    result = _GRAPH.invoke(
        {
            "spec": {
                "material": spec.material,
                "specification": spec.specification,
                "quantity": format(spec.quantity, "f"),
                "unit": spec.unit,
                "currency": spec.currency,
                "needed_by": spec.needed_by.isoformat(),
            },
            "offers": [_offer_dict(offer) for offer in offers],
            "as_of": as_of.isoformat(),
            "evaluated": [],
            "steps": [],
        }
    )
    ranked = [_result_from_dict(item) for item in result["evaluated"]]
    return ranked, list(result["steps"])


def _offer_dict(offer: CatalogueOffer) -> dict[str, str | None]:
    def money(value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value, "f")

    return {
        "supplier_id": offer.supplier_id,
        "supplier_name": offer.supplier_name,
        "quotation_id": offer.quotation_id,
        "material": offer.material,
        "specification": offer.specification,
        "available_quantity": format(offer.available_quantity, "f"),
        "capability_unit": offer.capability_unit,
        "lead_time_days": str(offer.lead_time_days),
        "unit_price": format(offer.unit_price, "f"),
        "currency": offer.currency,
        "quote_quantity": format(offer.quote_quantity, "f"),
        "quote_unit": offer.quote_unit,
        "freight_amount": money(offer.freight_amount),
        "tax_amount": money(offer.tax_amount),
        "discount_amount": money(offer.discount_amount),
        "tax_included": None if offer.tax_included is None else str(offer.tax_included).lower(),
        "valid_until": None if offer.valid_until is None else offer.valid_until.isoformat(),
    }
