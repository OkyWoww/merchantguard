"""Reproducible Synthetic Dataset Generator for MerchantGuard.

Generates realistic e-commerce dispute scenarios with courier telematics,
margin profiles, customer complaint texts, and deterministic ground truths.
"""

from __future__ import annotations
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any


def generate_synthetic_dataset(count: int = 50, seed: int = 42) -> List[Dict[str, Any]]:
    random.seed(seed)
    categories = [
        ("ITEM_NOT_RECEIVED", 0.45),
        ("DAMAGED", 0.25),
        ("NOT_AS_DESCRIBED", 0.20),
        ("UNAUTHORIZED_CHARGE", 0.10),
    ]

    complaints_bank = {
        "ITEM_NOT_RECEIVED": [
            "Tracking says delivered but porch was empty all day.",
            "I checked with my neighbors and nobody received this package.",
            "Package was marked left at front door but nothing is here.",
        ],
        "DAMAGED": [
            "Item arrived cracked in shipping box.",
            "Severe cosmetic damage to the outer casing upon unboxing.",
            "Glass element was shattered upon delivery.",
        ],
        "NOT_AS_DESCRIBED": [
            "Size and color are completely different from website photos.",
            "Specification does not match the product manual.",
        ],
        "UNAUTHORIZED_CHARGE": [
            "I did not recognize this credit card transaction on my statement.",
        ],
    }

    records = []
    base_date = datetime(2026, 9, 1, 10, 0, 0)

    for i in range(1, count + 1):
        case_id = f"CASE-{2000 + i}"
        order_id = f"ORD-{random.randint(10000, 99999)}"

        cat = random.choices([c[0] for c in categories], weights=[c[1] for c in categories])[0]
        complaint = random.choice(complaints_bank[cat])

        delivery_offset = random.randint(1, 30)
        claim_lag = random.randint(1, 35)

        delivery_dt = base_date + timedelta(days=delivery_offset)
        claim_dt = delivery_dt + timedelta(days=claim_lag)

        order_amount = round(random.uniform(15.0, 650.0), 2)
        margin_pct = random.uniform(0.20, 0.50)
        unit_margin = round(order_amount * margin_pct, 2)
        dispute_fee = 15.0

        geo_match = random.random() < 0.80
        sig_present = random.random() < 0.40 if order_amount > 150 else random.random() < 0.15

        events = [
            {
                "timestamp": (delivery_dt - timedelta(days=2)).isoformat() + "Z",
                "status": "IN_TRANSIT",
                "note": "Sorted at regional distribution hub",
                "geo_match": True,
                "signature_present": False,
            },
            {
                "timestamp": delivery_dt.isoformat() + "Z",
                "status": "DELIVERED",
                "note": "Package released to premises",
                "geo_match": geo_match,
                "signature_present": sig_present,
            },
        ]

        record = {
            "case_id": case_id,
            "order_id": order_id,
            "claim_date": claim_dt.isoformat() + "Z",
            "delivery_date": delivery_dt.isoformat() + "Z",
            "order_amount": order_amount,
            "unit_margin": unit_margin,
            "dispute_fee": dispute_fee,
            "claimed_reason": cat,
            "complaint_text": complaint,
            "courier_events": events,
        }
        records.append(record)

    return records


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent / "samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    dataset = generate_synthetic_dataset(20)
    out_file = out_dir / "synthetic_batch_20.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)
    print(f"Generated {len(dataset)} synthetic dispute cases in {out_file}")
