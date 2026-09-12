# /run-pbc-chase

Run one monitoring + chase cycle: check for new submissions, update statuses,
draft chases for eligible items, escalate/document non-response where due,
refresh the dashboard.

## Steps

1. Pull current Drive/inbox state. Against the sample fixtures, this is
   `sample_data/test_harness/Drive_Inbox_Submission_Log.xlsx`; in a live
   environment, use whichever Gmail/Drive access this Claude Code session has
   configured (see `CLAUDE.md`, "Integration decision not yet made").
2. Run:
   ```
   python scripts/match_submissions.py
   ```
3. Open `output/submission_classifications.json`. For every row with
   `needs_agent_review: true`, resolve it using the actual file/message
   content available to you — the script only got as far as metadata and
   keyword cues allow (see `CLAUDE.md`'s "What the code can and can't do").
4. Update the tracker's item statuses based on the resolved classifications.
   Use the Status enum from `docs/io-spec.md` B1 exactly — including
   "Rolled Forward — Confirmed No Change" and "Disputed — Pending Manager
   Adjudication," not ad hoc substitutes.
5. For every item not already Received/Rolled-Forward/Disputed, evaluate
   chase eligibility (`chase_engine.evaluate`). For each eligible item:
   a. Run `privacy_gate.check_transmission(entity, description, "email_attachment")`
      for anything you'd attach. If blocked, draft the secure-channel
      instruction template instead — never the file itself.
   b. Never draft anything for a Restricted-tier item. Surface it as a count
      to the partner instead.
   c. Draft (never send) a chase grouped by client contact and entity.
      Increment chase count; log to the Chase Log.
6. Run `chase_engine.should_escalate` and
   `chase_engine.should_draft_non_response_memo` for remaining items.
   Escalations and non-response memos are drafts for engagement-team review —
   never auto-filed or auto-sent.
7. Refresh the dashboard (`dashboard_builder.build_dashboard`) and present a
   summary: overall % complete, overdue/escalated/disputed counts, and
   anything blocked by the data-privacy gate this cycle.

## Reminders

- A disputed item gets no further chase drafts until the Manager responds.
- Materiality tier changes cadence only — never confidentiality, privacy, or
  dependency handling, even for a clearly immaterial item.
