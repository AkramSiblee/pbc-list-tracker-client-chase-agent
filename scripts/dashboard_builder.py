"""
dashboard_builder.py

Computes the rollup numbers behind the Dashboard tab described in
docs/io-spec.md B2: group rollup, per-entity, per-phase, and
materiality-weighted views, plus the data-privacy-exceptions and
disputed-items lanes. Pure computation over a list of tracker-item dicts —
no I/O beyond reading the tracker; writing an actual Google Sheet or local
Excel mirror is a separate concern (see scripts/build_master_tracker.py).
"""
from __future__ import annotations

from collections import defaultdict

COMPLETE_STATUSES = {"Received", "Rolled Forward — Confirmed No Change"}
OVERDUE_STATUSES = {"Overdue", "Escalated", "Non-Responsive"}


def _pct(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def rollup(items: list[dict], group_by: str) -> dict:
    """Generic rollup by any item field (entity, phase, materiality_tier)."""
    buckets: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        buckets[item.get(group_by) or "(unspecified)"].append(item)

    out = {}
    for key, bucket in buckets.items():
        total = len(bucket)
        complete = sum(1 for i in bucket if i.get("status") in COMPLETE_STATUSES)
        overdue = sum(1 for i in bucket if i.get("status") in OVERDUE_STATUSES)
        escalated = sum(1 for i in bucket if i.get("status") == "Escalated")
        disputed = sum(1 for i in bucket if i.get("status") == "Disputed — Pending Manager Adjudication")
        out[key] = {
            "total": total,
            "complete": complete,
            "pct_complete": _pct(complete, total),
            "overdue": overdue,
            "escalated": escalated,
            "disputed": disputed,
        }
    return out


def build_dashboard(items: list[dict], blocked_draft_count: int = 0) -> dict:
    group_total = len(items)
    group_complete = sum(1 for i in items if i.get("status") in COMPLETE_STATUSES)

    materiality_overdue = defaultdict(int)
    for i in items:
        if i.get("status") in OVERDUE_STATUSES:
            materiality_overdue[i.get("materiality_tier") or "(unclassified)"] += 1

    vendor_items = [i for i in items if i.get("vendor_specialist")]

    return {
        "group_rollup": {
            "total": group_total,
            "complete": group_complete,
            "pct_complete": _pct(group_complete, group_total),
            "overdue": sum(1 for i in items if i.get("status") in OVERDUE_STATUSES),
            "escalated": sum(1 for i in items if i.get("status") == "Escalated"),
        },
        "per_entity": rollup(items, "entity"),
        "per_phase": rollup(items, "phase"),
        "materiality_weighted_overdue": dict(materiality_overdue),
        "vendor_specialist_lane": rollup(vendor_items, "entity"),
        "data_privacy_exceptions_lane": {"blocked_draft_count": blocked_draft_count},
        "disputed_lane": [i["item_id"] for i in items if i.get("status") == "Disputed — Pending Manager Adjudication"],
    }


if __name__ == "__main__":
    sample_items = [
        {"item_id": "REV-01", "entity": "Meridian Global Holdings Inc.", "phase": "Interim",
         "materiality_tier": "Above Performance Materiality", "status": "Received"},
        {"item_id": "PPE-CA-01", "entity": "Meridian Manufacturing Co.", "phase": "Final",
         "materiality_tier": "Below Performance Materiality", "status": "Overdue"},
        {"item_id": "RPT-04", "entity": "Meridian Manufacturing Co.", "phase": "Final",
         "materiality_tier": "Specific-Risk (Regardless of Materiality)", "status": "Disputed — Pending Manager Adjudication"},
    ]
    import json
    print(json.dumps(build_dashboard(sample_items, blocked_draft_count=1), indent=2))
