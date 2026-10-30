"""Synthetic catalogue. These records are fictional and are not supplier offers."""

from uuid import UUID

DEMO_USER_ID = UUID("00000000-0000-4000-8000-000000000001")
DEMO_USER_EMAIL = "buyer@demo.local"
DEMO_APPROVER_ID = UUID("00000000-0000-4000-8000-000000000002")
DEMO_APPROVER_EMAIL = "approver@demo.local"

# unit_price is INR per tonne. Landed cost for 10 tonne uses freight and a zero discount.
# Harbour: 60000 * 10 + 20000 = 620000.00
# Metro: 61000 * 10 + 20000 = 630000.00
CATALOGUE = [
    {
        "supplier_id": UUID("00000000-0000-4000-8000-000000000101"),
        "quotation_id": UUID("00000000-0000-4000-8000-000000000201"),
        "capability_id": UUID("00000000-0000-4000-8000-000000000301"),
        "name": "Harbour Steel",
        "material": "TMT steel",
        "specification": "Fe 500D",
        "available_quantity": "20",
        "lead_time_days": 3,
        "unit_price": "60000",
        "freight_amount": "20000.00",
        "tax_amount": "0.00",
        "discount_amount": "0.00",
        "tax_included": True,
        "simulation_profile": {
            "minimum_unit_price": "58000.00",
            "concession_per_round": "1000.00",
        },
    },
    {
        "supplier_id": UUID("00000000-0000-4000-8000-000000000102"),
        "quotation_id": UUID("00000000-0000-4000-8000-000000000202"),
        "capability_id": UUID("00000000-0000-4000-8000-000000000302"),
        "name": "Metro Metals",
        "material": "TMT steel",
        "specification": "Fe 500D",
        "available_quantity": "15",
        "lead_time_days": 5,
        "unit_price": "61000",
        "freight_amount": "20000.00",
        "tax_amount": "0.00",
        "discount_amount": "0.00",
        "tax_included": True,
        "simulation_profile": {
            "minimum_unit_price": "60000.00",
            "concession_per_round": "500.00",
        },
    },
    {
        "supplier_id": UUID("00000000-0000-4000-8000-000000000103"),
        "quotation_id": UUID("00000000-0000-4000-8000-000000000203"),
        "capability_id": UUID("00000000-0000-4000-8000-000000000303"),
        "name": "Inland Mills",
        "material": "TMT steel",
        "specification": "Fe 415",
        "available_quantity": "40",
        "lead_time_days": 3,
        "unit_price": "1000",
        "freight_amount": "0.00",
        "tax_amount": "0.00",
        "discount_amount": "0.00",
        "tax_included": True,
        "simulation_profile": {
            "minimum_unit_price": "900.00",
            "concession_per_round": "50.00",
        },
    },
    {
        "supplier_id": UUID("00000000-0000-4000-8000-000000000104"),
        "quotation_id": UUID("00000000-0000-4000-8000-000000000204"),
        "capability_id": UUID("00000000-0000-4000-8000-000000000304"),
        "name": "Short Stock Yard",
        "material": "TMT steel",
        "specification": "Fe 500D",
        "available_quantity": "4",
        "lead_time_days": 2,
        "unit_price": "1000",
        "freight_amount": "0.00",
        "tax_amount": "0.00",
        "discount_amount": "0.00",
        "tax_included": True,
        "simulation_profile": {
            "minimum_unit_price": "900.00",
            "concession_per_round": "50.00",
        },
    },
    {
        "supplier_id": UUID("00000000-0000-4000-8000-000000000105"),
        "quotation_id": UUID("00000000-0000-4000-8000-000000000205"),
        "capability_id": UUID("00000000-0000-4000-8000-000000000305"),
        "name": "Distant Freight Co",
        "material": "TMT steel",
        "specification": "Fe 500D",
        "available_quantity": "30",
        "lead_time_days": 40,
        "unit_price": "1000",
        "freight_amount": "0.00",
        "tax_amount": "0.00",
        "discount_amount": "0.00",
        "tax_included": True,
        "simulation_profile": {
            "minimum_unit_price": "900.00",
            "concession_per_round": "50.00",
        },
    },
    {
        "supplier_id": UUID("00000000-0000-4000-8000-000000000106"),
        "quotation_id": UUID("00000000-0000-4000-8000-000000000206"),
        "capability_id": UUID("00000000-0000-4000-8000-000000000306"),
        "name": "Untaxed Traders",
        "material": "TMT steel",
        "specification": "Fe 500D",
        "available_quantity": "25",
        "lead_time_days": 4,
        "unit_price": "50000",
        "freight_amount": "0.00",
        "tax_amount": None,
        "discount_amount": "0.00",
        "tax_included": False,
        "simulation_profile": {
            "minimum_unit_price": "48000.00",
            "concession_per_round": "500.00",
        },
    },
]
