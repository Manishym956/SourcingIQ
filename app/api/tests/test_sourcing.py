from datetime import date, timedelta
from decimal import Decimal

from app.domain.sourcing import (
    CatalogueOffer,
    RfqSpec,
    evaluate_offer,
    quantize_money,
    rank_offers,
)


def _rfq(**overrides: object) -> RfqSpec:
    base = {
        "material": "TMT steel",
        "specification": "Fe 500D",
        "quantity": Decimal("10"),
        "unit": "tonne",
        "currency": "INR",
        "needed_by": date(2026, 11, 10),
    }
    base.update(overrides)
    return RfqSpec(**base)  # type: ignore[arg-type]


def _offer(**overrides: object) -> CatalogueOffer:
    base = {
        "supplier_id": "s1",
        "supplier_name": "Harbour Steel",
        "quotation_id": "q1",
        "material": "TMT steel",
        "specification": "Fe 500D",
        "available_quantity": Decimal("20"),
        "capability_unit": "tonne",
        "lead_time_days": 3,
        "unit_price": Decimal("60000"),
        "currency": "INR",
        "quote_quantity": Decimal("20"),
        "quote_unit": "tonne",
        "freight_amount": Decimal("20000"),
        "tax_amount": Decimal("0"),
        "discount_amount": Decimal("0"),
        "tax_included": True,
        "valid_until": None,
    }
    base.update(overrides)
    return CatalogueOffer(**base)  # type: ignore[arg-type]


AS_OF = date(2026, 11, 1)


def test_lowest_landed_cost_is_exact() -> None:
    result = evaluate_offer(_rfq(), _offer(), as_of=AS_OF)
    assert result.eligible
    assert result.landed_cost == Decimal("620000.00")
    assert result.exclusion_reasons == []


def test_tax_exclusive_adds_tax_once() -> None:
    result = evaluate_offer(
        _rfq(quantity=Decimal("1")),
        _offer(
            unit_price=Decimal("100"),
            freight_amount=Decimal("10"),
            tax_amount=Decimal("18"),
            discount_amount=Decimal("5"),
            tax_included=False,
            available_quantity=Decimal("5"),
        ),
        as_of=AS_OF,
    )
    assert result.landed_cost == Decimal("123.00")
    assert result.breakdown is not None
    assert result.breakdown["tax"] == "18.00"


def test_tax_included_is_not_added_again() -> None:
    result = evaluate_offer(
        _rfq(quantity=Decimal("1")),
        _offer(
            unit_price=Decimal("118"),
            freight_amount=Decimal("0"),
            tax_amount=Decimal("18"),
            tax_included=True,
            available_quantity=Decimal("5"),
        ),
        as_of=AS_OF,
    )
    assert result.landed_cost == Decimal("118.00")


def test_unknown_tax_is_not_treated_as_zero() -> None:
    result = evaluate_offer(
        _rfq(),
        _offer(tax_included=False, tax_amount=None),
        as_of=AS_OF,
    )
    assert result.eligible is False
    assert result.landed_cost is None
    assert "tax treatment is unknown" in result.exclusion_reasons[0]


def test_wrong_specification_is_ineligible_even_when_cheaper() -> None:
    result = evaluate_offer(
        _rfq(),
        _offer(specification="Fe 415", unit_price=Decimal("1"), supplier_name="Inland Mills"),
        as_of=AS_OF,
    )
    assert result.eligible is False
    assert "Fe 415" in result.exclusion_reasons[0]


def test_insufficient_quantity() -> None:
    result = evaluate_offer(_rfq(), _offer(available_quantity=Decimal("4")), as_of=AS_OF)
    assert result.eligible is False
    assert "available quantity is 4 tonne" in result.exclusion_reasons[0]


def test_late_delivery() -> None:
    result = evaluate_offer(_rfq(), _offer(lead_time_days=40), as_of=AS_OF)
    assert result.eligible is False
    assert "later than the requested deadline" in result.exclusion_reasons[0]


def test_missing_freight_is_not_zero() -> None:
    result = evaluate_offer(_rfq(), _offer(freight_amount=None), as_of=AS_OF)
    assert result.landed_cost is None
    assert "freight is missing" in result.exclusion_reasons[0]


def test_half_up_rounding() -> None:
    assert quantize_money(Decimal("10.005")) == Decimal("10.01")
    assert quantize_money(Decimal("10.004")) == Decimal("10.00")


def test_ranking_keeps_ineligible_offers_out_of_first_place() -> None:
    cheap_wrong = evaluate_offer(
        _rfq(),
        _offer(
            supplier_id="bad",
            supplier_name="Inland Mills",
            quotation_id="badq",
            specification="Fe 415",
            unit_price=Decimal("1"),
        ),
        as_of=AS_OF,
    )
    leader = evaluate_offer(_rfq(), _offer(), as_of=AS_OF)
    slower = evaluate_offer(
        _rfq(),
        _offer(
            supplier_id="s2",
            supplier_name="Metro Metals",
            quotation_id="q2",
            unit_price=Decimal("61000"),
            lead_time_days=5,
        ),
        as_of=AS_OF,
    )
    same_price_faster = evaluate_offer(
        _rfq(),
        _offer(
            supplier_id="s3",
            supplier_name="Fast Tie",
            quotation_id="q3",
            lead_time_days=1,
        ),
        as_of=AS_OF,
    )
    same_price_slower = evaluate_offer(
        _rfq(),
        _offer(
            supplier_id="s4",
            supplier_name="Slow Tie",
            quotation_id="q4",
            lead_time_days=3,
        ),
        as_of=AS_OF,
    )
    ranked = rank_offers([cheap_wrong, slower, same_price_slower, same_price_faster, leader])
    eligible = [item for item in ranked if item.eligible]
    assert eligible[0].supplier_name == "Fast Tie"
    assert "Lowest landed cost among eligible offers" in eligible[0].ranking_reasons
    assert ranked[-1].supplier_name == "Inland Mills"
    assert ranked[-1].eligible is False
    assert all(item.eligible for item in ranked[: len(eligible)])


def test_expired_offer() -> None:
    result = evaluate_offer(
        _rfq(),
        _offer(valid_until=AS_OF - timedelta(days=1)),
        as_of=AS_OF,
    )
    assert result.eligible is False
    assert "validity date" in result.exclusion_reasons[0]
