"""
generate_config.py

Reads sample_data/engagement_setup/Engagement_Setup_Package.xlsx and writes one
JSON file per tab into config/. Run this whenever the engagement setup workbook
changes (new entity onboarded, materiality reset, contact updated, etc.) so the
scripts and Claude Code skill always read current config rather than a stale copy.

Usage:
    python scripts/generate_config.py
"""
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "sample_data" / "engagement_setup" / "Engagement_Setup_Package.xlsx"
CONFIG_DIR = ROOT / "config"

# Maps each sheet name -> (output filename, header row number)
# Every sheet in this workbook has a merged title row (1), a blank row (2), and
# headers on row 3 or 4 (Contact Matrix/Entity Roster/Confidentiality/Materiality/
# Dependency/Vendor/Team/Cadence use row 3; Data Privacy Rules/Phase Calendar use
# row 3 as well) — but Entity Roster/Contact Matrix etc. were built with header at
# row 3 in build_setup_xlsx.py's make_sheet() helper. We detect the header row
# dynamically instead of hardcoding, to survive minor layout edits.
SHEETS = {
    "Entity Roster": "entity_roster.json",
    "Contact Matrix": "contact_matrix.json",
    "Confidentiality Rules": "confidentiality_rules.json",
    "Data Privacy Rules": "data_privacy_rules.json",
    "Materiality Thresholds": "materiality_thresholds.json",
    "Dependency Map": "dependency_map.json",
    "Phase Calendar": "phase_calendar.json",
    "Vendor-Specialist Register": "vendor_specialist_register.json",
    "Team & Escalation": "team_escalation.json",
    "Cadence Defaults": "cadence_defaults.json",
}


def slugify(header: str) -> str:
    return (
        header.strip()
        .lower()
        .replace("/", "_")
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace("?", "")
        .replace("-", "_")
    )


def find_header_row(ws) -> int:
    """The header row is the first row where every non-empty cell is a string
    and the row is immediately followed by at least one data row. In this
    workbook it's always row 3, but we scan up to row 6 to be tolerant of
    future edits."""
    for row_idx in range(1, 7):
        values = [c.value for c in ws[row_idx]]
        non_empty = [v for v in values if v not in (None, "")]
        if len(non_empty) >= 2 and all(isinstance(v, str) for v in non_empty):
            # Heuristic: header rows have short-ish string values, not one giant title string
            if all(len(str(v)) < 60 for v in non_empty):
                return row_idx
    raise ValueError(f"Could not locate header row in sheet '{ws.title}'")


def sheet_to_records(ws) -> list[dict]:
    header_row = find_header_row(ws)
    headers = [c.value for c in ws[header_row]]
    # Trim trailing empty header columns
    while headers and headers[-1] in (None, ""):
        headers.pop()
    keys = [slugify(h) for h in headers]

    records = []
    for row in ws.iter_rows(min_row=header_row + 1, max_col=len(headers)):
        values = [c.value for c in row]
        if all(v in (None, "") for v in values):
            continue
        record = {keys[i]: (values[i] if i < len(values) else None) for i in range(len(keys))}
        records.append(record)
    return records


def main():
    if not WORKBOOK.exists():
        print(f"ERROR: workbook not found at {WORKBOOK}", file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.load_workbook(WORKBOOK, data_only=True)
    CONFIG_DIR.mkdir(exist_ok=True)

    written = []
    for sheet_name, out_name in SHEETS.items():
        if sheet_name not in wb.sheetnames:
            print(f"WARNING: sheet '{sheet_name}' not found — skipping", file=sys.stderr)
            continue
        ws = wb[sheet_name]
        records = sheet_to_records(ws)
        out_path = CONFIG_DIR / out_name
        out_path.write_text(json.dumps(records, indent=2, default=str, ensure_ascii=False), encoding="utf-8")
        written.append((out_name, len(records)))

    print("Config files written:")
    for name, count in written:
        print(f"  {name}: {count} record(s)")


if __name__ == "__main__":
    main()
