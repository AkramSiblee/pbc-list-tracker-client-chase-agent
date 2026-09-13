# /add-component

Onboard a new entity/component mid-engagement (e.g. a business combination
like Meridian Nordics AB in the sample data) before any of its items enter
the chase pipeline.

## Steps

1. In `sample_data/engagement_setup/Engagement_Setup_Package.xlsx`, add rows
   for the new entity to:
   - **Entity Roster** — jurisdiction, functional/reporting currency,
     component type (note scope limitations, e.g. "opening balance sheet +
     purchase accounting only" for an in-year acquisition), auditor,
     reporting deadline.
   - **Contact Matrix** — at least one functional owner. It's normal for a
     newly acquired entity to have incomplete contacts (integration in
     progress) — record that explicitly rather than leaving it silently
     blank; route requests through an interim contact (e.g. the Group
     Controller) until resolved.
   - **Materiality Thresholds** — even a provisional figure, flagged as
     provisional if materiality hasn't been formally reassessed post-close.
   - **Data Privacy Rules** — if the entity is in a jurisdiction with its own
     data-protection regime, add the rule before any personal-data item for
     that entity is processed.
   - **Dependency Map** — if the new entity's deliverables block a group-level
     item (e.g. a purchase price allocation depending on an independent
     valuation), record it here.
   - **Vendor-Specialist Register** — if a specialist (e.g. a valuation firm)
     is involved, add them with a realistic lead time.
   - **Phase Calendar** — the new entity's fieldwork window, which is often
     narrower than a full-year component's.
2. Run:
   ```
   python scripts/generate_config.py
   ```
   and confirm the new entity appears in the relevant `output/config/*.json` files.
3. Only now run `/build-pbc-list` (or `extract_pbc_items.py` directly) to pull
   in the new entity's audit-program items — extraction before this point
   would create items with no registered contact, materiality, or dependency
   context.
4. Report to the user what was added and flag anything still incomplete
   (e.g. "Contact TBD — integration in progress") so it isn't forgotten.
