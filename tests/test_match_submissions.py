"""
Tests for scripts/match_submissions.py against the real
Drive_Inbox_Submission_Log.xlsx test harness. Requires extract_pbc_items.py
to have populated output/extracted_items.json (the population-entity map and
confidentiality map are read from it) — the fixture below regenerates it.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def ensure_extracted_items():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "extract_pbc_items.py")], check=True, capture_output=True)


@pytest.fixture(scope="module")
def classifications():
    from match_submissions import load_log_rows, load_population_entity_map, load_confidentiality_map, classify_row

    population_map = load_population_entity_map()
    confidentiality_map = load_confidentiality_map()
    rows = load_log_rows()
    return [classify_row(row, population_map, confidentiality_map) for row in rows]


def _by_date(classifications, date_str):
    matches = [c for c in classifications if str(c["date"]) == date_str]
    assert matches, f"No classified row found for date {date_str}"
    return matches[0]


def test_nineteen_rows_classified(classifications):
    assert len(classifications) == 19


def test_wrong_period_quality_fail_detected(classifications):
    assert _by_date(classifications, "2027-01-18")["action"] == "wrong_period_quality_fail"


def test_wrong_entity_content_mismatch_detected(classifications):
    assert _by_date(classifications, "2027-01-19")["action"] == "wrong_entity_content_mismatch"


def test_duplicate_id_resolved_by_entity_for_apac(classifications):
    assert _by_date(classifications, "2027-01-20")["action"] == "duplicate_id_resolved_by_entity"


def test_draft_version_pending_final(classifications):
    assert _by_date(classifications, "2027-01-22")["action"] == "draft_version_pending_final"


def test_final_version_supersedes_draft_and_releases_dependency(classifications):
    assert _by_date(classifications, "2027-02-14")["action"] == "final_version_received"


def test_ambiguous_reply_flagged_for_thread_tracing(classifications):
    result = _by_date(classifications, "2027-01-25")
    # two rows share this date; check the one matching the ambiguous-reply case
    matches = [c for c in classifications if str(c["date"]) == "2027-01-25"]
    actions = {c["action"] for c in matches}
    assert "ambiguous_reply_trace_thread" in actions
    assert "foreign_language_flagged" in actions


def test_restricted_item_with_fx_issue_routed_to_manual_log(classifications):
    result = _by_date(classifications, "2027-01-30")
    assert result["action"] == "restricted_item_manual_log"
    assert "FX" in result["detail"]


def test_restricted_non_response_still_flagged(classifications):
    result = _by_date(classifications, "2027-02-05")
    assert result["action"] == "restricted_item_manual_log"
    assert "non-response" in result["detail"].lower()


def test_vendor_direct_delivery_detected(classifications):
    assert _by_date(classifications, "2027-01-16")["action"] == "vendor_direct_delivery"


def test_low_confidence_scan_flagged(classifications):
    assert _by_date(classifications, "2027-01-28")["action"] == "low_confidence_scan_flagged"


def test_partial_submission_detected(classifications):
    assert _by_date(classifications, "2027-01-10")["action"] == "partial_submission"


def test_restricted_item_misrouted_to_standard_path(classifications):
    result = _by_date(classifications, "2027-01-12")
    assert result["action"] == "restricted_item_manual_log"
    assert "non-restricted-access path" in result["detail"]


def test_gdpr_block_on_caught_draft(classifications):
    assert _by_date(classifications, "2027-01-23")["action"] == "gdpr_block"


def test_client_dispute_detected_even_on_restricted_item(classifications):
    """RPT-05 is Restricted, but the dispute signal must still surface
    specifically rather than being swallowed by the generic manual-log flag."""
    assert _by_date(classifications, "2027-01-26")["action"] == "dispute_pending_manager"


def test_dispute_regex_does_not_false_positive_on_rollforward_language(classifications):
    """'package already provided at interim' must not trip the dispute
    detector — this is a rollforward representation, not pushback."""
    assert _by_date(classifications, "2027-01-05")["action"] == "rollforward_confirmed"


def test_sample_based_partial_names_outstanding_ids(classifications):
    result = _by_date(classifications, "2027-11-28")
    assert result["action"] == "partial_submission"


def test_every_row_gets_a_non_null_action(classifications):
    assert all(c["action"] is not None for c in classifications)
