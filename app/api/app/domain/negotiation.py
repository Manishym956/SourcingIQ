"""Deterministic mock negotiation. The simulator cannot change buyer bounds."""

from dataclasses import dataclass
from decimal import Decimal

from app.domain.sourcing import quantize_money

MAX_NEGOTIATION_ROUNDS = 5


@dataclass(frozen=True)
class NegotiationBounds:
    max_rounds: int
    floor_unit_price: Decimal
    ceiling_unit_price: Decimal


@dataclass(frozen=True)
class SupplierSimulation:
    list_unit_price: Decimal
    minimum_unit_price: Decimal
    concession_per_round: Decimal


@dataclass(frozen=True)
class TurnOutcome:
    accepted: bool
    round_count: int
    status: str
    buyer_unit_price: Decimal
    supplier_unit_price: Decimal
    reason: str


def bounds_error(bounds: NegotiationBounds) -> str | None:
    if bounds.max_rounds < 1 or bounds.max_rounds > MAX_NEGOTIATION_ROUNDS:
        return f"Maximum rounds must be from 1 to {MAX_NEGOTIATION_ROUNDS}."
    if bounds.floor_unit_price <= 0 or bounds.ceiling_unit_price <= 0:
        return "Price bounds must be greater than zero."
    if bounds.floor_unit_price > bounds.ceiling_unit_price:
        return "Floor unit price cannot exceed the ceiling."
    return None


def price_policy_error(bounds: NegotiationBounds, proposed: Decimal) -> str | None:
    if proposed < bounds.floor_unit_price:
        return "Proposed unit price is below the buyer floor."
    if proposed > bounds.ceiling_unit_price:
        return "Proposed unit price is above the buyer ceiling."
    return None


def supplier_ask(profile: SupplierSimulation, round_number: int) -> Decimal:
    reduced = profile.list_unit_price - (profile.concession_per_round * round_number)
    if reduced < profile.minimum_unit_price:
        reduced = profile.minimum_unit_price
    return quantize_money(reduced)


def apply_turn(
    bounds: NegotiationBounds,
    profile: SupplierSimulation,
    round_count: int,
    proposed: Decimal,
) -> TurnOutcome:
    """Advance one round. Caller must already reject prices outside the locked bounds."""
    next_round = round_count + 1
    ask = supplier_ask(profile, next_round)
    if proposed >= ask:
        return TurnOutcome(
            accepted=True,
            round_count=next_round,
            status="accepted",
            buyer_unit_price=quantize_money(proposed),
            supplier_unit_price=ask,
            reason="Buyer offer meets the simulated supplier ask.",
        )
    if next_round >= bounds.max_rounds:
        return TurnOutcome(
            accepted=False,
            round_count=next_round,
            status="limit_reached",
            buyer_unit_price=quantize_money(proposed),
            supplier_unit_price=ask,
            reason="Maximum rounds reached without acceptance.",
        )
    return TurnOutcome(
        accepted=False,
        round_count=next_round,
        status="open",
        buyer_unit_price=quantize_money(proposed),
        supplier_unit_price=ask,
        reason="Simulated supplier counteroffer.",
    )
