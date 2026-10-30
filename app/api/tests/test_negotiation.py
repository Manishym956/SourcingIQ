from decimal import Decimal

from app.domain.negotiation import (
    NegotiationBounds,
    SupplierSimulation,
    apply_turn,
    price_policy_error,
    supplier_ask,
)

HARBOUR = SupplierSimulation(
    list_unit_price=Decimal("60000"),
    minimum_unit_price=Decimal("58000"),
    concession_per_round=Decimal("1000"),
)
BOUNDS = NegotiationBounds(
    max_rounds=2,
    floor_unit_price=Decimal("57000"),
    ceiling_unit_price=Decimal("59000"),
)


def test_supplier_ask_steps_down_to_the_floor() -> None:
    assert supplier_ask(HARBOUR, 1) == Decimal("59000.00")
    assert supplier_ask(HARBOUR, 2) == Decimal("58000.00")
    assert supplier_ask(HARBOUR, 3) == Decimal("58000.00")


def test_buyer_offer_at_the_ask_is_accepted() -> None:
    outcome = apply_turn(BOUNDS, HARBOUR, 0, Decimal("59000"))
    assert outcome.accepted is True
    assert outcome.status == "accepted"
    assert outcome.round_count == 1
    assert outcome.buyer_unit_price == Decimal("59000.00")


def test_offer_below_the_ask_stays_open_until_the_round_cap() -> None:
    first = apply_turn(BOUNDS, HARBOUR, 0, Decimal("58000"))
    assert first.status == "open"
    assert first.supplier_unit_price == Decimal("59000.00")
    second = apply_turn(BOUNDS, HARBOUR, first.round_count, Decimal("57500"))
    assert second.status == "limit_reached"
    assert second.accepted is False
    assert second.round_count == 2


def test_price_outside_the_locked_bounds_is_rejected_before_a_round() -> None:
    assert price_policy_error(BOUNDS, Decimal("60000")) == (
        "Proposed unit price is above the buyer ceiling."
    )
    assert price_policy_error(BOUNDS, Decimal("56000")) == (
        "Proposed unit price is below the buyer floor."
    )
