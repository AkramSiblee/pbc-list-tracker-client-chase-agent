"""
chase_engine.py

Given a tracker item (as a dict) and today's date, decides whether it's
chase-eligible right now, and if not, why. Encodes the rules from
docs/skill-workflow.md Steps 9, 11, 13 and docs/io-spec.md B1/B8:

  - Restricted items are never automatically chase-eligible
  - Dependency-held items are never chase-eligible until the prerequisite is Received
  - Disputed items are never chase-eligible while pending Manager adjudication
  - Cadence is materiality-weighted: Above-Performance-Materiality and
    Specific-Risk items use the standard cadence; Below-Performance-Materiality
    items use the relaxed cadence
  - Vendor/specialist items use their own (longer) cadence, not the client cadence
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from utils import parse_date, business_days_between

ROOT = Path(__file__).resolve().parents[1]
CADENCE_PATH = ROOT / "config" / "cadence_defaults.json"

NON_CHASEABLE_STATUSES = {
    "Received",
    "Rolled Forward — Confirmed No Change",
    "Disputed — Pending Manager Adjudication",
    "Not Yet Requested",
}


@dataclass
class ChaseDecision:
    eligible: bool
    reason: str
    cadence_days: int | None = None


def _default_cadence_days(item: dict) -> int:
    """Business days between chases, before any override. Mirrors
    config/cadence_defaults.json in spirit; kept as plain constants here so
    the engine has no hard dependency on the config file's exact wording,
    which is meant for humans to read."""
    if item.get("vendor_specialist"):
        return 10
    if item.get("source") == "Fieldwork Sample":
        return 5
    materiality = (item.get("materiality_tier") or "").lower()
    if "below performance materiality" in materiality and "specific-risk" not in materiality:
        return 7
    return 3  # Above Performance Materiality or Specific-Risk, or unclassified — default to the stricter cadence


def evaluate(item: dict, today: dt.date | None = None) -> ChaseDecision:
    today = today or dt.date.today()

    status = item.get("status", "Requested")
    if status in NON_CHASEABLE_STATUSES:
        return ChaseDecision(False, f"Status is '{status}' — not chase-eligible by design.")

    if (item.get("confidentiality_tier") or item.get("confidentiality")) == "Restricted":
        return ChaseDecision(False, "Restricted-tier item — never enters the automated chase pipeline (partner-handled only).")

    depends_on = item.get("depends_on")
    dependency_received = item.get("dependency_received", True)
    if depends_on and not dependency_received:
        return ChaseDecision(False, f"Dependency-held: waiting on {depends_on} before this item can be chased.")

    due_date = parse_date(item.get("due_date"))
    if due_date and due_date > today:
        return ChaseDecision(False, f"Not yet due (due {due_date.isoformat()}).")

    cadence_days = _default_cadence_days(item)
    last_chase = parse_date(item.get("last_chase_date"))
    if last_chase is None:
        return ChaseDecision(True, "No prior chase — eligible now.", cadence_days)

    elapsed = business_days_between(last_chase, today)
    if elapsed >= cadence_days:
        return ChaseDecision(True, f"{elapsed} business day(s) since last chase >= cadence ({cadence_days}).", cadence_days)
    return ChaseDecision(False, f"Only {elapsed} business day(s) since last chase; cadence is {cadence_days}.", cadence_days)


def should_escalate(item: dict, escalation_threshold: int = 2) -> bool:
    """Above-threshold chase count, not disputed, not Restricted (Restricted
    items escalate to Partner at creation, not via chase-count threshold —
    see Step 15)."""
    if item.get("status") in ("Disputed — Pending Manager Adjudication", "Received", "Rolled Forward — Confirmed No Change"):
        return False
    if (item.get("confidentiality_tier") or item.get("confidentiality")) == "Restricted":
        return False
    return (item.get("chase_count") or 0) >= escalation_threshold


def should_draft_non_response_memo(item: dict, today: dt.date | None = None,
                                    chase_threshold: int = 4, days_threshold: int = 10) -> bool:
    """Fires on chase count OR days-overdue, whichever comes first — applies
    even to Restricted items, which otherwise never get auto-chased (Step 15)."""
    today = today or dt.date.today()
    if (item.get("chase_count") or 0) >= chase_threshold:
        return True
    due_date = parse_date(item.get("due_date"))
    if due_date:
        overdue_days = business_days_between(due_date, today)
        if overdue_days >= days_threshold:
            return True
    return False


if __name__ == "__main__":
    # Mirrors the "materiality-based cadence (negative test)" case in
    # Drive_Inbox_Submission_Log.xlsx: an immaterial item 11 business days
    # overdue with only 1 chase should NOT be escalation-eligible yet.
    sample_item = {
        "item_id": "PPE-CA-01",
        "materiality_tier": "Below Performance Materiality",
        "status": "Overdue",
        "due_date": "2027-01-20",
        "last_chase_date": "2027-01-25",
        "chase_count": 1,
    }
    decision = evaluate(sample_item, today=dt.date(2027, 2, 5))
    print("Chase decision:", decision)
    print("Escalate?", should_escalate(sample_item))
