import datetime as dt

from chase_engine import evaluate, should_escalate, should_draft_non_response_memo


def test_restricted_item_never_chase_eligible():
    item = {"item_id": "RPT-04", "confidentiality_tier": "Restricted", "status": "Requested", "due_date": "2027-01-01"}
    decision = evaluate(item, today=dt.date(2027, 2, 1))
    assert decision.eligible is False
    assert "Restricted" in decision.reason


def test_dependency_held_item_never_chase_eligible():
    item = {
        "item_id": "PEN-01", "confidentiality_tier": "Sensitive", "status": "Requested",
        "due_date": "2027-01-01", "depends_on": "PEN-DE-01", "dependency_received": False,
    }
    decision = evaluate(item, today=dt.date(2027, 2, 1))
    assert decision.eligible is False
    assert "Dependency-held" in decision.reason


def test_disputed_item_never_chase_eligible():
    item = {"item_id": "RPT-05", "status": "Disputed — Pending Manager Adjudication", "due_date": "2027-01-01"}
    decision = evaluate(item, today=dt.date(2027, 2, 1))
    assert decision.eligible is False


def test_not_yet_due_item_not_eligible():
    item = {"item_id": "REV-01", "status": "Requested", "due_date": "2099-01-01"}
    decision = evaluate(item, today=dt.date(2027, 2, 1))
    assert decision.eligible is False
    assert "Not yet due" in decision.reason


def test_below_materiality_item_uses_relaxed_cadence():
    item = {
        "item_id": "PPE-CA-01", "status": "Overdue", "due_date": "2027-01-20",
        "materiality_tier": "Below Performance Materiality", "last_chase_date": "2027-01-25",
    }
    # 6 business days since last chase — below the relaxed 7-day cadence
    not_yet = evaluate(item, today=dt.date(2027, 2, 2))
    assert not_yet.eligible is False
    assert not_yet.cadence_days == 7

    # 9 business days since last chase — now eligible again
    now_eligible = evaluate(item, today=dt.date(2027, 2, 5))
    assert now_eligible.eligible is True


def test_above_materiality_item_uses_standard_3_day_cadence():
    item = {
        "item_id": "REV-01", "status": "Overdue", "due_date": "2027-01-20",
        "materiality_tier": "Above Performance Materiality", "last_chase_date": "2027-01-25",
    }
    decision = evaluate(item, today=dt.date(2027, 1, 27))  # 2 business days later
    assert decision.eligible is False
    assert decision.cadence_days == 3


def test_vendor_specialist_uses_10_day_cadence():
    item = {
        "item_id": "PEN-DE-01", "status": "Overdue", "due_date": "2027-01-01",
        "vendor_specialist": "Hoffmann Versicherungsmathematik GmbH", "last_chase_date": "2027-01-10",
    }
    decision = evaluate(item, today=dt.date(2027, 1, 15))  # 3 business days later, cadence is 10
    assert decision.eligible is False
    assert decision.cadence_days == 10


def test_materiality_never_relaxes_escalation_threshold_once_reached():
    """Materiality changes cadence, never the escalation rule itself — an
    immaterial item with 2+ chases is still escalation-eligible."""
    item = {"item_id": "PPE-CA-01", "materiality_tier": "Below Performance Materiality", "status": "Overdue", "chase_count": 2}
    assert should_escalate(item) is True


def test_immaterial_item_with_one_chase_does_not_escalate():
    """The negative test from Drive_Inbox_Submission_Log.xlsx: don't
    over-escalate an immaterial item that's only been chased once."""
    item = {"item_id": "PPE-CA-01", "materiality_tier": "Below Performance Materiality", "status": "Overdue", "chase_count": 1}
    assert should_escalate(item) is False


def test_restricted_item_never_escalates_via_chase_count():
    item = {"item_id": "RPT-04", "confidentiality_tier": "Restricted", "status": "Overdue", "chase_count": 5}
    assert should_escalate(item) is False


def test_non_response_memo_fires_on_chase_count_threshold():
    item = {"item_id": "RPT-04", "chase_count": 4, "due_date": "2027-02-01"}
    assert should_draft_non_response_memo(item, today=dt.date(2027, 2, 5)) is True


def test_non_response_memo_fires_on_days_overdue_even_with_zero_chases():
    """Restricted items are never auto-chased, so chase_count stays 0 — but
    the days-overdue path must still fire (Step 15)."""
    item = {"item_id": "RPT-04", "confidentiality_tier": "Restricted", "chase_count": 0, "due_date": "2027-01-01"}
    assert should_draft_non_response_memo(item, today=dt.date(2027, 1, 20)) is True
