"""
Tests for scripts/extract_pbc_items.py against the real sample audit programs.

Run scripts/extract_pbc_items.py at least once before running these tests, or
run via pytest which invokes extraction fresh in the fixture below.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def extracted():
    out_path = ROOT / "output" / "extracted_items_test.json"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "extract_pbc_items.py"), "--out", str(out_path)],
        check=True, capture_output=True, text=True,
    )
    return json.loads(out_path.read_text())


def test_extracts_all_four_programs(extracted):
    entities = {item["entity"] for item in extracted}
    assert entities == {
        "Meridian Global Holdings Inc.",
        "Meridian Europe GmbH",
        "Meridian Asia Pacific Pte Ltd",
        "Meridian Manufacturing Co.",
    }


def test_parent_schedule_a_items_present(extracted):
    parent_ids = {item["item_id"] for item in extracted if item["entity"] == "Meridian Global Holdings Inc."}
    expected = {
        "REV-01", "REV-02", "PPE-01", "PPE-02", "PAY-01", "PAY-02", "RPT-01",
        "GC-01", "GC-02", "LIT-01", "ITGC-01", "PEN-01", "GOV-01", "PPA-01", "VAL-NORDICS-01",
    }
    assert expected <= parent_ids


def test_apac_duplicate_item_id_extracted_cleanly(extracted):
    """Guards against the pdfplumber wrapped-cell-newline bug: REV-01 must be
    a clean token, not 'REV-APAC-\\n02' or similar."""
    apac_ids = {item["item_id"] for item in extracted if item["entity"] == "Meridian Asia Pacific Pte Ltd"}
    assert "REV-01" in apac_ids
    assert all("\n" not in i and " " not in i for i in apac_ids)


def test_restricted_items_tagged(extracted):
    pay02 = next(i for i in extracted if i["item_id"] == "PAY-02" and i["entity"] == "Meridian Global Holdings Inc.")
    assert pay02["confidentiality"] == "Restricted"


def test_exactly_expected_items_flagged_for_review(extracted):
    """Only the two narrative cross-references (RPT-04 mentioned in Parent's
    text, RPT-01 mentioned in Manufacturing Co.'s text) and the Europe GmbH
    item missing a due date should be flagged — nothing else."""
    flagged = {(i["item_id"], i["entity"]) for i in extracted if i["needs_review"]}
    assert flagged == {
        ("RPT-04", "Meridian Global Holdings Inc."),
        ("RPT-01", "Meridian Manufacturing Co."),
        ("PEN-DE-01", "Meridian Europe GmbH"),
    }


def test_europe_missing_due_date_flagged(extracted):
    pen_de = next(i for i in extracted if i["item_id"] == "PEN-DE-01")
    assert "due_date" in pen_de.get("missing_fields", [])
