---
name: pbc-list-tracker-client-chase-agent
description: Generates PBC lists from audit programs (single-entity or group/component), tracks receipt across Drive and inbox, drafts phase- and materiality-aware chase emails, enforces confidentiality and data-privacy gates, and maintains a live dashboard. Use when the user asks to build a PBC list, chase outstanding client documents, update the tracker, onboard a new component/entity mid-engagement, or check PBC status.
---

# PBC List Tracker & Client Chase Agent

Full methodology: `docs/skill-workflow.md`. Full data contracts: `docs/io-spec.md`.
Known gotchas and non-negotiable rules: `CLAUDE.md` at the repo root — read it
before running anything in this skill.

This skill wraps a set of deterministic Python scripts (`scripts/`) with the
judgment calls that only Claude should make. **The scripts decide what's
mechanically determinable; you decide everything that depends on actually
understanding content, and you always hold the line on the rules below even
when a script doesn't check for you.**

## Rules you enforce personally, not just via script

- Never draft or send a client-facing email for a **Restricted**-tier item.
  Check `config/confidentiality_rules.json` and the item's tier before
  drafting anything, even if a script's output suggests an item is
  chase-eligible — Restricted items should never reach that stage, but if a
  bug in this repo lets one through, you are the last line of defense.
- Never attach a file to a drafted email without running it past
  `scripts/privacy_gate.py` (`check_transmission`) first, using the item's
  entity and a description of what's in the file. A "Sensitive" (not
  Restricted) item can still be blocked — don't skip this because the
  confidentiality tier looked fine.
- When `scripts/match_submissions.py` flags a row `needs_agent_review: true`,
  actually read the submitted file (or its content, if available to you) and
  resolve it — don't just pass the flag through to the dashboard unresolved
  if you have the means to settle it.
- When onboarding a new entity (business combination, new component), update
  `sample_data/engagement_setup/Engagement_Setup_Package.xlsx` (Entity Roster,
  Contact Matrix, Materiality Thresholds, Dependency Map tabs) and re-run
  `scripts/generate_config.py` **before** any item for that entity is allowed
  into the chase pipeline. Don't let an incoming file for an unregistered
  entity get auto-processed.
- If a client reply disputes an item's necessity, do not draft a further
  chase. Set the item's status to "Disputed — Pending Manager Adjudication"
  and surface the client's question to the Manager. Only the Manager's
  response reopens the item.

## Workflow

### 1. Build the PBC list (new engagement, or new component mid-engagement)

1. Confirm `config/*.json` is current — if `sample_data/engagement_setup/
   Engagement_Setup_Package.xlsx` changed, run `python scripts/generate_config.py`.
2. Run `python scripts/extract_pbc_items.py`. Read `output/extracted_items.json`.
3. For every item with `needs_review: true`, resolve it yourself: read the
   surrounding document context (`raw_context` field), decide the correct
   entity/description/owner, and correct the record. Common cases you'll see
   in this repo's sample data: a narrative cross-reference to another entity's
   item (e.g. Parent's program mentioning "see Item RPT-04" — that's
   Manufacturing Co.'s item, not the Parent's), and a program that's simply
   missing a due date.
4. Present the reviewed list to the engagement team for confirmation before
   anything goes client-facing (per `docs/skill-workflow.md` Step 3).
5. Run `python scripts/build_master_tracker.py` to initialize the tracker.
   Check the printed "Dependency-held on init" list — those items should not
   be requested from the client yet.

### 2. Monitor and chase (recurring run)

1. Pull current Drive/inbox state (via whatever connector this Claude Code
   environment has configured — see `CLAUDE.md`'s "Integration decision not
   yet made" section; against the sample fixtures, this is
   `sample_data/test_harness/Drive_Inbox_Submission_Log.xlsx`).
2. Run `python scripts/match_submissions.py` for the first-pass classification.
   For every `needs_agent_review: true` row, resolve it using actual content —
   the script only got you as far as metadata and keyword cues allow.
3. Update tracker item statuses based on resolved classifications (Received /
   Partial / Rolled Forward / Disputed / etc. — see the Status enum in
   `docs/io-spec.md` B1).
4. For each item, call `chase_engine.evaluate(item, today)` to determine chase
   eligibility. For eligible items:
   - Run `privacy_gate.check_transmission(...)` before attaching anything.
   - Draft (never send) a chase grouped by client contact and entity.
   - Increment chase count, log to the Chase Log.
5. Call `chase_engine.should_escalate(item)` and
   `chase_engine.should_draft_non_response_memo(item, today)` for items past
   threshold. Escalation and non-response memos are drafted for engagement
   team review, never auto-filed.
6. Run `python scripts/dashboard_builder.py`-equivalent logic (import
   `build_dashboard` and call it with the current tracker items) to refresh
   the dashboard view.

### 3. Answer a status question

Read the current tracker (`output/Master_Tracker.xlsx` for the local mirror,
or the live Sheet if connected) and use `dashboard_builder.build_dashboard()`
rather than re-deriving rollups by hand — it already implements the
group/entity/phase/materiality-weighted views the spec calls for.

## Slash commands available

- `/build-pbc-list` — runs Workflow step 1 end-to-end
- `/run-pbc-chase` — runs Workflow step 2 end-to-end
- `/add-component` — onboarding checklist for a new entity mid-engagement
- `/pbc-dashboard` — refreshes and presents the dashboard

## Test coverage

`tests/` has 48 tests covering extraction (against all four real sample
audit-program formats), the privacy gate, the chase engine, the submission
classifier (all 19 real test-harness rows), and the dashboard builder. Run
`python -m pytest tests/ -v` after any change to `scripts/`. If you add a new
rule to `docs/skill-workflow.md` or `docs/io-spec.md`, add a corresponding
test and — where the rule needs one — a fixture row in
`sample_data/test_harness/Drive_Inbox_Submission_Log.xlsx`, consistent with
how every existing rule has at least one test case exercising it.
