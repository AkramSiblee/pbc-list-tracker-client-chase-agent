# /pbc-dashboard

Refresh and present the current PBC status dashboard.

## Steps

1. Load the current tracker (`output/Master_Tracker.xlsx` for the local
   mirror, or the live Sheet if this session has one connected). If it
   doesn't exist yet or looks stale, run `python scripts/build_master_tracker.py`
   first.
2. Convert the tracker rows to the dict shape `dashboard_builder.build_dashboard`
   expects (see its docstring and `tests/test_dashboard_builder.py` for the
   field names) and call it.
3. Present, in this order:
   - Group rollup (% complete, overdue, escalated)
   - Per-entity view (call out any component significantly behind the others)
   - Materiality-weighted overdue counts — lead with above-materiality and
     specific-risk overdue items; mention below-materiality overdue items
     separately and without urgency framing
   - Vendor/specialist lane (these have their own lead times — don't compare
     them to client-cadence overdue items)
   - Disputed items lane — these are waiting on a Manager response, not on
     the client
   - Data-privacy exceptions this period (blocked-draft count), if any

## Reminders

- Never let a below-materiality overdue item crowd out an above-materiality
  or specific-risk one in how you present urgency, even if there are more of
  the former.
- Restricted items appear as a count only, never with detail, unless the
  person asking is the partner.
