"""
match_submissions.py

A rule-based FIRST-PASS classifier for incoming Drive/inbox submissions
(sample_data/test_harness/Drive_Inbox_Submission_Log.xlsx). It is intentionally
narrow: it catches the patterns that are mechanically detectable from
structured fields and keyword cues (entity mismatch via known population,
dispute language, rollforward language, GDPR-blockable channel+data-type
combinations, draft-vs-final filename cues, vendor-direct delivery).

What this script does NOT try to do — and where real judgment is still
required from whoever (or whichever agent) operationalizes this live — is
anything that depends on actually reading the submitted file's *content*
(e.g., confirming a fixed asset schedule's figures are for the wrong fiscal
year, or judging OCR confidence on a scanned signature page). Those cases are
flagged as `needs_agent_review` rather than silently resolved. This mirrors
the "explicit over silent" principle in docs/skill-workflow.md Section 6.

Usage:
    python scripts/match_submissions.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import find_item_ids, canonical_entity  # noqa: E402
from privacy_gate import check_transmission  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "sample_data" / "test_harness" / "Drive_Inbox_Submission_Log.xlsx"
EXTRACTED_PATH = ROOT / "output" / "extracted_items.json"

DISPUTE_MARKERS = re.compile(r"already audited|why (do you |does (this|it) )?need|disput|please confirm this is (actually )?needed", re.IGNORECASE)
ROLLFORWARD_MARKERS = re.compile(r"no significant change|no change since interim|rolled? ?forward", re.IGNORECASE)
DRAFT_MARKERS = re.compile(r"\bdraft\b|entwurf|preliminary|subject to review", re.IGNORECASE)
FINAL_MARKERS = re.compile(r"\bfinal\b|\bsigned\b", re.IGNORECASE)
VENDOR_DIRECT_MARKERS = re.compile(r"delivered (directly )?by the vendor|vendor-direct|delivered directly", re.IGNORECASE)
LOW_CONFIDENCE_SCAN_MARKERS = re.compile(r"scan|ocr|illegible|poor scan", re.IGNORECASE)
PARTIAL_MARKERS = re.compile(r"\bpartial\b|only .* (tab|schedule|sub-component) (was )?provided|missing", re.IGNORECASE)
AMBIGUOUS_REPLY_MARKERS = re.compile(r"sent last week|see attached", re.IGNORECASE)
NO_ATTACHMENT_MARKERS = re.compile(r"no attachment", re.IGNORECASE)
BLOCKED_DRAFT_SOURCE = re.compile(r"caught pre-send", re.IGNORECASE)
WRONG_PERIOD_MARKERS = re.compile(r"last year'?s|prior year|previous year|re-uploaded by mistake|different (fiscal )?year|not fy\d{2}", re.IGNORECASE)
FX_MARKERS = re.compile(r"currency|\bfx\b", re.IGNORECASE)
FOREIGN_LANGUAGE_MARKERS = re.compile(r"in german|not translated|foreign.?language", re.IGNORECASE)
MISROUTED_MARKERS = re.compile(r"restricted-access location|rather than a restricted|general .*folder", re.IGNORECASE)

SHORT_ENTITY_MARKERS = {
    "Meridian Global Holdings Inc.": "Global Holdings",
    "Meridian Europe GmbH": "Europe GmbH",
    "Meridian Asia Pacific Pte Ltd": "Asia Pacific",
    "Meridian Manufacturing Co.": "Manufacturing Co",
    "Meridian Nordics AB": "Nordics AB",
}


def load_confidentiality_map() -> dict[tuple[str, str], str]:
    """(item_id, entity) -> confidentiality tier, from the static-program extraction."""
    if not EXTRACTED_PATH.exists():
        return {}
    items = json.loads(EXTRACTED_PATH.read_text())
    return {(item["item_id"], item["entity"]): item.get("confidentiality") for item in items if item.get("confidentiality")}


def load_population_entity_map() -> dict[str, set[str]]:
    """item_id -> set of entities it legitimately belongs to, built from the
    static-program extraction. Multiple entities can legitimately share an
    Item ID string (e.g., REV-01 exists at both Parent and APAC) — that's the
    real-world collision this function exists to help resolve."""
    if not EXTRACTED_PATH.exists():
        return {}
    items = json.loads(EXTRACTED_PATH.read_text())
    mapping: dict[str, set[str]] = {}
    for item in items:
        mapping.setdefault(item["item_id"], set()).add(item["entity"])
    return mapping


def classify_row(row: dict, population_map: dict[str, set[str]], confidentiality_map: dict[tuple[str, str], str]) -> dict:
    entity_raw = row.get("entity_as_filed_received") or ""
    entity = canonical_entity(entity_raw) or entity_raw
    filename = row.get("file_name___email_subject") or ""
    item_ref = row.get("item_reference_as_submitted") or ""
    note = row.get("content_note") or ""
    source = row.get("source") or ""

    result = {
        "date": row.get("date"),
        "entity": entity,
        "filename": filename,
        "item_reference": item_ref,
        "action": None,
        "needs_agent_review": False,
        "detail": None,
    }

    ids_in_ref = find_item_ids(item_ref)
    item_id = ids_in_ref[0] if ids_in_ref else item_ref

    # 0. Confidentiality hard gate — Restricted items never run through standard
    # automated matching, full stop (see docs/skill-workflow.md Section 6).
    # Content-level flags (FX, misrouting) are appended as context, not branched
    # into separate outcomes, because the routing decision is the same either way.
    if confidentiality_map.get((item_id, entity)) == "Restricted":
        # Even a Restricted item's inbound reply can carry an actionable
        # dispute or rollforward signal — those routes are more specific than
        # a blanket manual-log flag, so they take precedence here too.
        if DISPUTE_MARKERS.search(note):
            result["action"] = "dispute_pending_manager"
            result["needs_agent_review"] = True
            result["detail"] = "Restricted item disputed by client — route to Manager for adjudication (still never auto-chased)."
            return result
        if ROLLFORWARD_MARKERS.search(note):
            result["action"] = "rollforward_confirmed"
            result["detail"] = "Restricted item — no-change representation received; mark Rolled Forward (still partner-reviewed, not auto-processed)."
            return result
        extra = []
        if source == "None received":
            extra.append("non-response threshold logic still applies for Non-Response Memo purposes")
        if FX_MARKERS.search(note):
            extra.append("FX-consistency issue noted in Changelog")
        if MISROUTED_MARKERS.search(note):
            extra.append("found in a non-restricted-access path — confidentiality-handling exception for Partner review")
        result["action"] = "restricted_item_manual_log"
        result["needs_agent_review"] = True
        result["detail"] = "Restricted-tier item — routed to partner, not processed via standard automated matching." + (
            " Additional flags: " + "; ".join(extra) if extra else ""
        )
        return result

    # 1. GDPR pre-send block: a caught draft attaching personal data
    if BLOCKED_DRAFT_SOURCE.search(source):
        privacy = check_transmission(entity, f"{filename} {note}", channel="email_attachment")
        if privacy.blocked:
            result["action"] = "gdpr_block"
            result["detail"] = privacy.reason
            return result

    # 2. Non-response (nothing to match — an absence, not a submission)
    if source == "None received":
        result["action"] = "non_response_candidate"
        result["detail"] = "No submission received past due date — evaluate against non-response memo threshold."
        return result

    # 3. Client dispute
    if DISPUTE_MARKERS.search(note):
        result["action"] = "dispute_pending_manager"
        result["detail"] = "Client contests the item's necessity — pause chase, route to Manager."
        return result

    # 4. Interim-to-final rollforward representation
    if ROLLFORWARD_MARKERS.search(note):
        result["action"] = "rollforward_confirmed"
        result["detail"] = "Written no-change representation — mark Rolled Forward, no resubmission required."
        return result

    # 5. Vendor-direct delivery
    if VENDOR_DIRECT_MARKERS.search(note):
        result["action"] = "vendor_direct_delivery"
        result["detail"] = "Delivered by the vendor/specialist directly — log source distinctly from client contact."
        return result

    # 6. Wrong-period content flag (a real quality-fail, not just low confidence)
    if WRONG_PERIOD_MARKERS.search(note):
        result["action"] = "wrong_period_quality_fail"
        result["needs_agent_review"] = True
        result["detail"] = "Note indicates the submitted content is for the wrong fiscal period — revert to Requested, log in Changelog."
        return result

    # 7. Wrong-entity content mismatch — a different entity's short name is
    # mentioned in the note text than the one this row was filed under. A real
    # script can only catch this when the mismatch is described in metadata or
    # notes; catching it purely from the submitted file's own content is
    # agent-level judgment and isn't attempted here.
    for canonical_name, marker in SHORT_ENTITY_MARKERS.items():
        if canonical_name != entity and marker in note:
            result["action"] = "wrong_entity_content_mismatch"
            result["needs_agent_review"] = True
            result["detail"] = f"Note references {canonical_name}, not the filed entity {entity} — route for manual confirmation rather than auto-assigning."
            return result

    # 8. FX / multi-currency inconsistency
    if FX_MARKERS.search(note):
        result["action"] = "fx_inconsistency_flagged"
        result["needs_agent_review"] = True
        result["detail"] = "Multi-currency inconsistency noted — surface on dashboard, do not block status."
        return result

    # 9. Duplicate Item ID / entity resolution
    known_entities = population_map.get(item_id, set())
    if len(known_entities) > 1:
        if entity in known_entities:
            result["action"] = "duplicate_id_resolved_by_entity"
            result["detail"] = f"'{item_id}' is shared across {sorted(known_entities)}; folder/content indicates {entity}."
        else:
            result["action"] = "duplicate_id_needs_resolution"
            result["needs_agent_review"] = True
            result["detail"] = f"'{item_id}' collides across {sorted(known_entities)}; filed entity '{entity}' not in the known set — needs manual confirmation."
        return result

    # 10. Final version supersedes a prior draft — checked ahead of the generic
    # draft marker below, because a note describing a final delivery often
    # still mentions "the draft" in passing (e.g. "...three weeks after the
    # draft"), which must not re-flag the final delivery as still pending.
    # Filenames use underscores as word separators, which don't count as \b
    # boundaries in regex — normalize to spaces before matching.
    filename_normalized = re.sub(r"[_\-]", " ", filename)
    if FINAL_MARKERS.search(filename_normalized) and not DRAFT_MARKERS.search(filename_normalized):
        result["action"] = "final_version_received"
        result["detail"] = "Filename/content indicates the FINAL version — mark Received as a new version; check dependency_map.json for items that can now be released."
        return result

    # 11. Draft vs final versioning
    if DRAFT_MARKERS.search(note) or DRAFT_MARKERS.search(filename_normalized):
        result["action"] = "draft_version_pending_final"
        result["detail"] = "Marked draft/preliminary — record as a version, do not mark Received."
        return result

    # 12. Ambiguous reply requiring thread tracing
    if source.lower().startswith("gmail reply") and AMBIGUOUS_REPLY_MARKERS.search(note):
        result["action"] = "ambiguous_reply_trace_thread"
        result["needs_agent_review"] = True
        result["detail"] = "Reply references an earlier attachment without one present in this message — trace the thread before updating status."
        return result

    # 13. Low-confidence scan
    if LOW_CONFIDENCE_SCAN_MARKERS.search(note):
        result["action"] = "low_confidence_scan_flagged"
        result["needs_agent_review"] = True
        result["detail"] = "Scan/OCR confidence concern — extract what's legible, flag fields individually."
        return result

    # 14. Foreign-language document (graduated flag, does not block)
    if FOREIGN_LANGUAGE_MARKERS.search(note):
        result["action"] = "foreign_language_flagged"
        result["detail"] = "Document not in engagement language — flag for translation, still counts toward Received."
        return result

    # 15. Partial submission (including named sample IDs outstanding)
    if PARTIAL_MARKERS.search(note):
        result["action"] = "partial_submission"
        result["detail"] = "Mark Partial; if this is a sample-based item, Notes must name the specific outstanding references."
        return result

    result["action"] = "standard_receive"
    result["detail"] = "No special handling pattern matched — proceed with standard quality check and mark Received if it passes."
    return result


def load_log_rows() -> list[dict]:
    wb = openpyxl.load_workbook(LOG_PATH, data_only=True)
    ws = wb.active
    header_row = 4  # per build_submissionlog_xlsx.py layout
    headers = [
        str(c.value).strip().lower().replace("(", "").replace(")", "").replace(" ", "_").replace("/", "_")
        for c in ws[header_row] if c.value
    ]
    rows = []
    for row in ws.iter_rows(min_row=header_row + 1, max_col=len(headers)):
        values = [c.value for c in row]
        if all(v in (None, "") for v in values):
            continue
        rows.append(dict(zip(headers, values)))
    return rows


def main():
    population_map = load_population_entity_map()
    confidentiality_map = load_confidentiality_map()
    if not population_map:
        print("NOTE: run scripts/extract_pbc_items.py first for duplicate-ID resolution to work.", file=sys.stderr)

    rows = load_log_rows()
    results = [classify_row(row, population_map, confidentiality_map) for row in rows]

    out_path = ROOT / "output" / "submission_classifications.json"
    out_path.write_text(json.dumps(results, indent=2, default=str, ensure_ascii=False))

    for r in results:
        flag = " [NEEDS AGENT REVIEW]" if r["needs_agent_review"] else ""
        print(f"{r['date']} | {r['entity']:32} | {r['action']:32}{flag}")

    print(f"\n{len(results)} row(s) classified. Written to {out_path}")


if __name__ == "__main__":
    main()
