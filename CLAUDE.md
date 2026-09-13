# CLAUDE.md — PBC List Tracker & Client Chase Agent

Persistent context for every Claude Code session in this repo. Read this
before touching anything. The authoritative specs are in `docs/` — this file
is conventions, known failure modes, and how the pieces fit together, not a
restatement of the spec.

## What this is

An agent that generates a PBC (Prepared By Client) list from one or more
audit programs, tracks receipt across a multi-entity Drive/inbox structure,
drafts chase emails, and maintains a live dashboard — built to survive
Big 4-caliber group-audit complexity (multiple components, confidentiality
tiers, GDPR/data-residency constraints, materiality-weighted urgency,
dependency chains, client disputes, interim-to-final rollforward, and
fieldwork-generated sample requests).

Read `docs/skill-workflow.md` and `docs/io-spec.md` first. They define the
rules. This repo implements them.

## Non-negotiable rules (never relax these, in code or in judgment)

1. **Draft-only. Always.** No script or command in this repo sends an email.
   Everything terminates in a Gmail *draft* for human review.
2. **Confidentiality is a hard gate, not a chase parameter.** Restricted-tier
   items (`output/config/confidentiality_rules.json`) never enter the automated
   chase pipeline. `scripts/chase_engine.py` and `scripts/match_submissions.py`
   both enforce this independently — if you add a new code path that touches
   chasing or drafting, it must check confidentiality tier too.
3. **Data privacy is orthogonal to confidentiality, and runs first.**
   `scripts/privacy_gate.py` can block a transmission for an item that is only
   "Sensitive" (not Restricted) — e.g. the German payroll register, which is
   GDPR-scoped but not confidentiality-Restricted. Never assume confidentiality
   tier alone tells you whether something can go out by email.
4. **Materiality changes urgency, never handling.** A below-materiality item
   gets a slower chase cadence (`chase_engine._default_cadence_days`). It never
   gets looser confidentiality, privacy, or dependency treatment.
5. **Explicit over silent.** Low-confidence extractions, ambiguous matches,
   quality-failed receipts, and content the scripts can't verify (wrong period,
   wrong entity based on figures inside a file) are flagged
   (`needs_agent_review` / `needs_review`), never silently resolved or dropped.

## What the code can and can't do — read this before "fixing" a classification

`scripts/match_submissions.py` is a **rule-based first-pass classifier**, not
a full agent. It catches patterns detectable from filenames, metadata, and
note/reply text (dispute language, rollforward language, draft/final filename
cues, entity names mentioned in passing text, GDPR-blockable channel+data-type
combinations). It deliberately does **not** try to verify a submitted file's
actual content — e.g. it cannot tell that a schedule's figures are for the
wrong fiscal year by reading the numbers. Rows requiring that kind of judgment
are flagged `needs_agent_review: true` and are meant to be resolved by Claude
Code operating live with real file content in context, not by adding more
regexes here. If you're tempted to add a regex to catch one more sample-data
row, ask whether the underlying signal is actually metadata-detectable in the
real world, or whether it's content-dependent and belongs in agent judgment
instead.

## Known failure modes (already fixed once — don't reintroduce)

- **pandoc default table output.** `pandoc -t markdown` renders docx tables
  built without an explicit header-row style as *grid tables* (dashes/plus
  signs), not pipe tables — nearly impossible to parse reliably. We use
  `pandoc -t gfm` instead, which forces pipe tables. GFM also has a quirk:
  a table with no declared header row renders an *empty* header + separator,
  with the real header labels appearing as the first body row. See
  `extract_from_docx()` in `scripts/extract_pbc_items.py` for the handling —
  don't "simplify" this by going back to plain `-t markdown`.
- **pdfplumber wrapped-cell newlines.** Table cells with wrapped text can come
  back containing literal `\n` characters mid-token (e.g. `REV-APAC-\n02`).
  Always normalize with `.replace("\n", " ")` and collapse whitespace before
  treating a cell value as an Item ID. See `extract_from_pdf()`.
- **Regex word boundaries on underscored filenames.** `\bfinal\b` will *not*
  match inside `Aktuarsgutachten_FINAL.pdf` because `_` counts as a word
  character in regex, so there's no boundary between `_` and `F`. Normalize
  filenames (`_`/`-` → space) before applying `\b`-bounded keyword regexes.
  See `filename_normalized` in `scripts/match_submissions.py`.
- **Check priority order matters more than any individual regex.** In
  `match_submissions.classify_row`, confidentiality (Restricted) is checked
  *before* dispute/rollforward/GDPR/duplicate-ID logic, but dispute and
  rollforward are re-checked *inside* the Restricted branch too — a Restricted
  item can still carry an actionable dispute signal, and that's more useful
  than a blanket "manual log" flag. Similarly, "final version received" must
  be checked before the generic draft-keyword check, because a note describing
  a final delivery often still mentions "the draft" in passing (referring to
  the superseded prior version). If you reorder these checks, re-run
  `tests/test_match_submissions.py` — it exercises all 19 real test-harness
  rows and will catch a regression immediately.
- **Multiple dependencies per item.** An item can depend on more than one
  prerequisite (e.g. `RPT-01` depends on both `RPT-04` and `RPT-05`). Don't
  collapse `dependency_map.json` into a single-dependency-per-item dict — use
  a list per `(item_id, entity)` key, as `build_master_tracker.apply_dependencies`
  does.

## Repo conventions

- **Config is generated, not hand-edited.** `output/config/*.json` is produced
  by `scripts/generate_config.py` from `sample_data/engagement_setup/
  Engagement_Setup_Package.xlsx`. If engagement setup changes (new entity,
  new contact, revised materiality), edit the workbook and regenerate — don't
  hand-edit the JSON, it'll just get overwritten.
- **`sample_data/` is the single input root**; **`output/` is the single
  output root** (scratch space, not committed deliverables) — generated
  config, tracker mirrors, classification results, and extracted-item dumps
  all land under `output/` and are regenerated by re-running the relevant
  script.
- **Sample data is real (well-formed) test fixtures, not placeholders.** The
  four audit programs, the engagement setup workbook, the fieldwork sample
  requests, and the 19-row submission log in `sample_data/` were built to
  exercise every rule in `docs/skill-workflow.md` and `docs/io-spec.md` at
  least once. Treat them as regression fixtures — if you change a rule, check
  whether a sample-data row now needs a matching update.
- **Git as audit trail.** Config regeneration, extraction runs, and any
  materiality/confidentiality rule change should be a distinct, reviewable
  commit — this is the paper trail an audit engagement would actually want.

## Integration decision not yet made: live Gmail/Drive access

This agent was originally scoped to run in Claude Cowork using its built-in
Gmail and Google Drive connectors (see `docs/skill-workflow.md` Section 9,
"Cowork Execution Notes"). Running it from Claude Code in VS Code instead
means one of two paths needs to be chosen before the live chase/monitor steps
(not the deterministic scripts in this repo, which need no live access) can
actually run against real Gmail/Drive:

1. **MCP servers configured for this Claude Code environment**, mirroring
   Cowork's connector model — if available, `.claude/commands/run-pbc-chase.md`
   should call those tools directly, following the same draft-only,
   privacy-gated, confidentiality-gated rules enforced in
   `scripts/privacy_gate.py` and `scripts/chase_engine.py`.
2. **Direct Google API integration via OAuth** (the pattern used in the
   BizInfoGraph AR/Collection Agent build) — `gmail.compose` scope only
   (never `gmail.send`), full `drive` scope (not `drive.file`, which only
   sees app-created files — see the AR agent's `google-api-lessons.md` for
   why this matters).

Neither is wired up yet. Everything in `scripts/` is connector-agnostic and
works against local file fixtures; whichever path is chosen, it's an
additional integration layer on top of these scripts, not a replacement for
them.

## Running things

```bash
# One-time / whenever engagement setup changes:
python scripts/generate_config.py

# Core pipeline, in order:
python scripts/extract_pbc_items.py          # -> output/extracted_items.json
python scripts/build_master_tracker.py       # -> output/Master_Tracker.xlsx
python scripts/match_submissions.py          # -> output/submission_classifications.json

# Ad hoc checks:
python scripts/privacy_gate.py               # smoke test
python scripts/chase_engine.py               # smoke test
python scripts/dashboard_builder.py          # smoke test

# Full test suite (48 tests, all passing as of this writing):
python -m pytest tests/ -v
```

Requires `pandoc` on PATH (used for docx parsing) in addition to the Python
packages in `requirements.txt`.
