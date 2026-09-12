# /build-pbc-list

Build (or rebuild) the PBC list and initialize the Master Tracker for this
engagement.

## Steps

1. If `sample_data/engagement_setup/Engagement_Setup_Package.xlsx` has changed
   since `config/*.json` was last generated, run:
   ```
   python scripts/generate_config.py
   ```
2. Run:
   ```
   python scripts/extract_pbc_items.py
   ```
3. Open `output/extracted_items.json`. For every item with `needs_review: true`:
   - Read its `raw_context` (for narrative-only items) or check
     `missing_fields` (for structured items missing a due date, etc.)
   - Resolve it: correct the entity/description/owner, or confirm the item
     should stay flagged for the engagement team's own confirmation.
4. Present the reviewed, entity-grouped list to the user for confirmation.
   Do not proceed past this point without confirmation — this mirrors
   `docs/skill-workflow.md` Step 3 (Manager/Partner sign-off, especially for
   Restricted-tier routing).
5. Once confirmed, run:
   ```
   python scripts/build_master_tracker.py
   ```
6. Report the result: total rows written, and the "Dependency-held on init"
   list — explain to the user which items cannot be requested from the client
   yet and why (per `config/dependency_map.json`).

## Notes

- If this is a new component being added mid-engagement (e.g. a business
  combination), see `/add-component` first — the entity needs to exist in
  `config/entity_roster.json`, `config/contact_matrix.json`, and
  `config/materiality_thresholds.json` before its items are extracted here.
