# PBC List Tracker & Client Chase Agent — IO Spec

## Part A — Input File Requirements

### A1. Audit Program(s)

**Accepted formats:** Word (.docx), Excel (.xlsx), PDF (text-based or scanned).

**Structural variants the agent must handle** (real-world variation across firms/templates):
- Single-entity program vs. **group audit** — one program per component, each potentially in a different format from the others
- Narrative-style programs (PBC items embedded in procedure text, e.g., "obtain client's fixed asset continuity schedule...") vs. structured checklist tabs with dedicated PBC columns
- ISA-section-tagged programs (Revenue, PPE, Payroll, Related Parties, Going Concern, Litigation, ITGC, etc.) vs. flat unsectioned lists
- Prior-year carryforward PBC lists (recurring items reused year over year, often with stale contact names)
- Scanned/image PDF programs requiring OCR fallback
- Business combination / purchase accounting addenda issued mid-engagement when a new component is acquired (scope limited to opening balance sheet, purchase price allocation, and stub-period results — not a full-year program)

**Required metadata alongside the program** (not always in the document itself — must be supplied separately if missing):
- Entity/component name, jurisdiction, functional currency, reporting currency
- Fieldwork phase calendar: Planning / Interim / Year-End–Final / Subsequent Events / Wrap-up, with a due-date window per phase
- Group vs. component reporting deadline (component deadlines are typically earlier than group)

**Extraction confidence handling:** every extracted item carries a confidence score. Below threshold → routed to the Changelog for manual confirmation, never silently included or dropped.

### A2. Engagement Setup Data

- **Entity/component roster** — for group audits: list of all components, their auditors (group vs. component team), and which PBC items apply to which entities
- **Contact matrix** — client-side owner per functional area *per entity*: Controller (GL/close), Treasury (cash/debt), Payroll/HR, Tax, IT (systems, access), Legal (confirmations, litigation), and a Component Controller for each subsidiary. A single "client contact" field is insufficient for Big 4-scale engagements
- **Engagement team hierarchy** — Staff / Senior / Manager / Partner, mapped to escalation tiers
- **Confidentiality rules** — firm- or engagement-defined criteria for Standard / Sensitive / Restricted (typical Restricted examples: legal confirmations, executive compensation, related-party transaction detail, fraud or whistleblower matters — never auto-chased)
- **Dependency map** — optional item-to-item prerequisites (e.g., final adjusting journal entries required before final trial balance can be requested)
- **Chase cadence + escalation thresholds** — defaults (chase every 3 business days; escalate after 2 unanswered chases) overridable per entity or phase
- **Vendor/specialist register** — third parties who deliver PBC items directly (payroll processor SOC 1 report, actuary, external valuator, IT specialist) with their own lead times and contacts
- **Materiality thresholds** — group/component materiality, performance materiality, and clearly trivial threshold per entity; used only to set chase urgency, never to loosen confidentiality, privacy, or dependency handling. Items scoped in for a specific risk (e.g., a related-party component) are tagged as such regardless of how low their materiality is
- **Data privacy / residency rules** — per entity and data type: whether it contains personal data, the applicable regime (GDPR, PDPA, PIPEDA, etc.), and the permitted transfer mechanism. This is a separate axis from Confidentiality Tier: a Sensitive (not Restricted) item like a foreign payroll register can still be transfer-restricted and must never be attached to a plain email

### A6. Sample-Based / Fieldwork-Generated PBC Requests (second input stream)

- Distinct from the static audit program: these items are generated **during** interim or final testing once a statistical or judgmental sample is pulled, and cannot be known in advance
- Each item references a **Population Item ID** (the program-level item it was sampled from) and lists the specific sampled references (transaction IDs, employee IDs, SKUs, asset tags)
- Carries its own expedited due date, shorter than program-level items, because fieldwork testing windows are fixed
- Inherits confidentiality and data-privacy flags independently — a sample pulled from a Sensitive/GDPR-scoped population (e.g., a payroll sample) carries the same transfer restrictions as the population item, even though it's a new row
- Partial receipt on a sample item must name which specific sampled references are still outstanding — never a generic "partial"

### A3. Shared Drive Structure

- Expected shape: one root engagement folder → one subfolder per entity/component → optional subfolders per functional area
- Agent reads existing structure; does not assume file-naming conventions are followed — matching relies on filename **and** light content inspection, not filename alone
- Requires Drive access broad enough to see client-created folders/files, not only agent-created ones

### A4. Inbox

- One engagement mailbox (or per-entity mailbox for large group audits) with read + draft-create access
- Agent parses both attachments and reply body text (clients often reply "sent last week, see attached" without re-stating which item)

### A5. Known Input Failure Modes to Handle

- Missing contact for a given area/entity
- Missing or conflicting due dates across program vs. engagement calendar
- Duplicate Item IDs within an entity, or the same item appearing in both group and component programs
- Documents in a language other than the agreed engagement language
- Multi-currency figures within a single submitted schedule (flagged for FX consistency, not analyzed)
- Draft/preliminary submissions later superseded by a final version
- An attempt (by a team member or an auto-generated draft) to attach cross-border-restricted personal data to a plain email — must be caught before send, not after
- A client contact disputing an item's necessity or applicability instead of simply not responding — different from non-response and requires different handling
- A client providing a "no significant change since interim" representation instead of a fresh document at final fieldwork
- A new entity/component appearing mid-engagement (acquisition) before its contacts, materiality, and dependencies have been fully set up

---

## Part B — Output Specification

### B1. Master Tracker (Google Sheet, multi-entity, one workbook per engagement)

| Column | Notes |
|---|---|
| Engagement ID | e.g. CLIENTABC-FY26 |
| Entity/Component | subsidiary or parent |
| Audit Area | e.g. Revenue, Payroll, ITGC |
| Phase | Planning / Interim / Final / Subsequent Events / Wrap-up |
| Item ID | unique within entity |
| PBC Item Description | |
| Source | Static Audit Program / Fieldwork Sample — distinguishes the two input streams |
| Population Item ID | if Source = Fieldwork Sample, the program-level item it was sampled from |
| Owner/Contact | functional owner, entity-specific |
| Confidentiality Tier | Standard / Sensitive / Restricted |
| Data Privacy Flag | None / Personal Data — [Regime] (e.g. "Personal Data — GDPR"); governs transmission channel independently of Confidentiality Tier |
| Materiality Tier | Above Performance Materiality / Below Performance Materiality / Specific-Risk (Regardless of Materiality) — governs chase cadence only |
| Depends On | Item ID prerequisite, if any |
| Vendor/Specialist | Y/N + third-party name if applicable |
| Date Requested | plain text YYYY-MM-DD |
| Due Date | plain text YYYY-MM-DD |
| Status | Not Yet Requested (dependency-held) / Requested / Received / Partial / Rolled Forward — Confirmed No Change / Overdue / Disputed — Pending Manager Adjudication / Escalated / Non-Responsive |
| Date Received | plain text YYYY-MM-DD |
| File Link | Drive link, current version |
| Version | v1, v2... with prior versions retained, not overwritten |
| Chase Count | |
| Last Chase Date | |
| Notes | for Partial sample items, names the specific outstanding sample references |

### B2. Dashboard Tab

- **Group rollup view** — overall % complete, overdue count, escalated count across all entities
- **Per-entity view** — same metrics filtered to one component (critical for group audits where different components close on different timelines)
- **Per-phase view** — Planning/Interim/Final/Subsequent Events/Wrap-up completion, since a single entity has different due-date windows per phase
- **Vendor/specialist lane** — separate view for third-party-delivered items given their longer, non-client-controlled lead times
- **Materiality-weighted view** — above-materiality and specific-risk overdue items surfaced separately from below-materiality overdue items, so the latter never crowds out what actually matters
- **Data-privacy exceptions lane** — count of blocked-draft events (personal data caught before send) per entity, for engagement team awareness
- **Disputed items lane** — items paused for Manager adjudication, distinct from ordinary overdue/escalated items
- Status color coding; overdue and escalated items surfaced at top; Restricted items shown as a count only (not detail) to non-partner viewers

### B3. Chase Log

- One row per chase draft created: timestamp, entity, recipient, items referenced, Gmail draft link, chase number in sequence
- Vendor/specialist chases logged separately from client chases

### B4. Changelog

- Every flagged item: low-confidence extraction, ambiguous file match, quality-failed receipt (wrong entity/period, illegible), missing contact/due date, duplicate Item ID
- Status column: "Pending — awaiting [engagement team/client] confirmation"

### B5. Version History Log

- Tracks every file version received per item: version number, date, submitter, superseded-by link
- Never deletes a prior version's record

### B6. Non-Response Memo (drafted document, not a sheet row)

- Triggered when an item passes the firm-set non-response threshold
- Contents: item description, entity, chase history (dates/count), contact(s) chased, escalation record, and a placeholder for engagement team's assessment of audit evidence impact
- Drafted for the engagement file — routed to Manager/Partner, never finalized or filed automatically

### B7. Chase Email Content (drafts only)

- **Standard/Sensitive items:** grouped by client contact and entity — one email per contact listing their outstanding items, not one email per item
- **Restricted items:** never drafted by the agent; surfaced only as a flagged count to the partner
- **Vendor/specialist items:** separate template acknowledging longer lead times, addressed to the third-party contact on record
- **Data-privacy-blocked items:** never drafted with the file attached; the substitute draft instructs the client to use the firm's secure portal, and never contains the personal data itself
- **Disputed items:** no further chase draft is generated while Status = "Disputed — Pending Manager Adjudication"; the agent surfaces the dispute to the Manager instead

### B10. Component Reporting Package (per significant component, for the group file)

- A structured summary — separate from the internal Dashboard — that a component team or the agent produces back to the group engagement team: PBC completion % for that component, outstanding items with reasons, any disputed or non-responsive items, and materiality-relevant gaps
- Mirrors the kind of deliverable a component auditor would return under a group reporting instruction (ISA 600) — this agent produces the tracking data behind it, not the formal instruction itself
- Drafted for engagement team review, not sent externally

### B8. Two-Tier Flagging Framework

- **Structural (hard gate)** — missing contact, duplicate Item ID, unreadable program section, dependency not yet satisfied, personal data about to be transferred outside an approved channel: blocks the item (or the specific draft) from proceeding
- **Graduated (item-level)** — low-confidence match, partial submission, approaching due date, foreign-language document, FX inconsistency, below-materiality overdue status: surfaced on dashboard, does not block
- Note: the data-privacy hard gate blocks a *transmission*, not the item's status — the item can still be Received once submitted through the approved channel; only the plain-email path is blocked

### B9. Pre-Delivery Checklist

- [ ] All extracted items reviewed and approved per entity before any client-facing send
- [ ] Confidentiality classification reviewed by Manager/Partner, especially Restricted-tier routing
- [ ] No Standard/Sensitive item missing both contact and due date without a Changelog entry
- [ ] Dependency map validated — no circular dependencies
- [ ] Chase drafts reviewed before send (draft-only enforced end to end)
- [ ] Dashboard rollups reconcile to Master Tracker counts, per entity and overall
- [ ] Non-Response Memos routed to Partner, not auto-filed
- [ ] No draft exists where a data-privacy flag should have blocked it — spot-check the blocked-draft log against the Data Privacy Rules tab
- [ ] Materiality tiers applied consistently — no above-materiality or specific-risk item sitting at a relaxed cadence
- [ ] All Disputed items have a logged Manager response or remain explicitly open — none silently re-entered the chase cycle
- [ ] Any new component added mid-engagement has full Contact Matrix, Materiality Threshold, and Dependency Map entries before its items were chased
