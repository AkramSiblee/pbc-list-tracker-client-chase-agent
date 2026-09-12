---
name: pbc-list-tracker-client-chase-agent
description: Generates PBC (Prepared By Client) lists from one or more audit programs (single-entity or group/component), tracks receipt across a multi-entity Drive structure and inbox, drafts phase- and contact-aware chase emails, escalates through both engagement and client hierarchies, and maintains a live multi-client, multi-entity status dashboard — built for Big 4-caliber engagement complexity.
trigger_phrases: ["build the PBC list", "set up the group PBC tracker", "chase outstanding PBC items", "update the PBC tracker", "run the PBC chase", "PBC status dashboard", "draft a non-response memo", "log a sample request", "add a new component/acquisition to the tracker", "flag a materiality/data-privacy exception"]
non_triggers: ["testing or reviewing the substance of received PBC documents (separate automations)", "formal ISA 600 component auditor instruction/communication protocol (agent supports tracking only, not the audit methodology itself)", "legal privilege or partner-only sign-off decisions", "auto-sending any client-facing email without review", "resolving a client dispute or scope disagreement on the agent's own authority", "setting or overriding materiality, or deciding what qualifies as personal data under a given privacy regime — the agent applies rules it's given, it does not set them", "financial statement analysis, JE testing, revenue contract review, risk assessment memo, or fraud brainstorming (see other automations in the suite)"]
build: Cowork (Gmail connector + Google Drive connector + Google Sheets, minimal custom code)
---

# PBC List Tracker & Client Chase Agent — Skill & Workflow

## 1. Purpose

Eliminate manual "did the client send X yet" admin on engagements with real-world complexity: multiple legal entities/components, multiple client-side owners per area, phased fieldwork (interim/final), specialist and third-party (vendor) dependencies, and confidentiality-sensitive items that can't be handled by blanket automation. Built for use by Big 4-caliber teams where a single engagement can span dozens of entities and hundreds of PBC line items.

## 2. Scope Boundaries

**In scope:** PBC list generation, receipt tracking, chase drafting, escalation, dashboarding, non-response documentation support.
**Out of scope (hard boundary):** substantive review/testing of received documents; formal ISA 600 group instruction issuance; any decision requiring partner judgment (confidentiality overrides, materiality calls, non-cooperation consequences); auto-sending anything client-facing.

## 3. Required Inputs

- One or more **audit programs** per engagement (single entity, or one per component in a group audit) — Word, Excel, or PDF, structure varies by firm/template
- **Entity/component structure**: parent + subsidiaries, jurisdiction, functional currency, reporting currency, local vs group fieldwork dates
- **Contact matrix**: client-side owner per functional area per entity (Controller, Treasury, Payroll/HR, Tax, IT, Legal, Component controller) — not a single client contact
- **Engagement team hierarchy**: Staff/Senior/Manager/Partner mapped to escalation tiers
- **Confidentiality classification rules**: what counts as Sensitive (limited-access) vs Restricted (partner-only) — e.g., legal confirmations, executive compensation, related-party items, fraud/whistleblower matters
- **Phase calendar**: Planning / Interim / Year-End–Final / Subsequent Events / Wrap-up, each with its own due-date window
- **Dependency map** (optional but common): items that cannot be requested/chased until a prerequisite item is received (e.g., final adjusting entries before final trial balance; a purchase price allocation blocked on an independent valuation)
- **Materiality thresholds** per entity: group/component materiality, performance materiality, clearly trivial threshold — drives chase urgency, never confidentiality or data-privacy handling
- **Data privacy / residency rules**: which data types contain personal data, the applicable regime (GDPR, PDPA, PIPEDA, etc.), and whether cross-border transfer requires a channel other than plain email — orthogonal to confidentiality tier; a Sensitive (not Restricted) item can still be transfer-restricted
- **Sample-based / fieldwork-generated PBC requests** (second, dynamic input stream): items that don't exist until a sample is pulled during interim or final testing, each referencing the population-level item it came from, with its own expedited due date
- Shared Drive structure (per-entity or per-area subfolders) and Gmail inbox access per engagement mailbox
- Chase cadence + escalation thresholds, configurable per entity/phase/materiality tier (defaults: chase every 3 business days; escalate after 2 unanswered chases; relaxed 7-business-day cadence for items below performance materiality and not tied to a specific risk)

## 4. Execution Steps (with per-step outputs)

1. **Ingest audit program(s)** — one per entity/component if group audit → extract PBC items with area, description, phase tag, suggested functional owner → *Output: draft item list per entity*
2. **Classify each item** — confidentiality tier, dependency links, vendor/specialist flag, materiality tier (Above/Below Performance Materiality, or Specific-Risk-Regardless-of-Materiality), and data-privacy flag (personal data Y/N + regime) → *Output: enriched item list*
3. **Confirm with engagement team** (Manager/Partner sign-off on scope, especially Restricted-tier and data-privacy routing) before anything is client-facing → *Output: approved PBC list per entity*
4. **Initialize Master Tracker** rows across all entities; send phase-appropriate initial requests (Standard/Sensitive items via drafted email to the correct functional owner; Restricted items flagged to the partner for manual handling, never auto-drafted) → *Output: tracker rows, initial Gmail drafts, Restricted-item flag list*
5. **Ingest sample-based/fieldwork-generated items** on an ongoing basis as they arrive throughout interim and final testing — each new row references its population-level item and inherits an expedited due date → *Output: new tracker rows tagged Source = "Fieldwork Sample"*
6. **Monitor** Drive (per-entity folders) + inbox each run → match incoming files/replies to tracker rows by filename/keyword/content, entity, and area → *Output: status updates, File Link + Version populated*
7. **Data-privacy gate** — before any draft is created or any file is referenced in a client-facing communication, check the item's data-privacy flag; if personal data under a cross-border-restricted regime (e.g., GDPR) is detected in what would be attached, block the draft and substitute the secure-channel instruction template instead → *Output: blocked-draft log entry, rerouted instruction*
8. **Quality-check receipt** — wrong entity/period, illegible, or missing sub-component → item reverts to "Requested" with reason logged (does not count toward completeness); draft/preliminary vs final versions tracked, not overwritten → *Output: Version History entry*
9. **Dependency gate** — item stays "Not Yet Requested" until its prerequisite is Received → *Output: dependency-held items excluded from active chase*
10. **Rollforward check (interim → final)** — where a client provides a written "no significant change since interim" representation instead of a fresh package, mark the item "Rolled Forward — Confirmed No Change" and retain the interim support as the basis, rather than demanding resubmission → *Output: rollforward log entry*
11. **Chase cycle** — scan for Standard/Sensitive items past their materiality-weighted cadence threshold, not yet received, not dependency-held, not disputed → draft chase grouped by client contact and entity (Restricted items excluded from automated chase) → *Output: Gmail drafts, Chase Count +1, Chase Log entry*
12. **Vendor/specialist chase** — items requiring third-party delivery (service org SOC reports, actuarial/valuation reports) routed on a separate longer-lead cadence, flagged distinctly on dashboard → *Output: vendor chase drafts, lead-time flag*
13. **Dispute handling** — if a client contact disputes an item's applicability or necessity, do not continue chasing: mark "Disputed — Pending Manager Adjudication," pause the chase clock, and route the client's question to the Manager for response → *Output: disputed-item flag, chase paused*
14. **Escalate** — past-threshold, non-disputed items flagged up both chains: engagement (Senior→Manager→Partner) and client (Preparer→Reviewer/Controller→CFO) → *Output: Escalated flag*
15. **Non-response documentation** — sustained non-response past a firm-set threshold triggers a drafted Non-Response Memo (for audit evidence/ISA 500 purposes), not a further chase; applies even to Restricted items, which are otherwise never auto-chased → *Output: memo draft for engagement file*
16. **Scope change / new component onboarding** — when a new entity is added mid-engagement (e.g., a business combination), extend the Master Tracker, Contact Matrix, Materiality Thresholds, and Dependency Map to cover it before any items for that entity enter the chase pipeline; new-component contacts are frequently incomplete (integration in progress) and must not block the rest of the engagement's cadence → *Output: new entity onboarded into all tracker structures*
17. **Refresh dashboard** every run — group rollup, per-entity, per-phase, and per-materiality-tier views → *Output: updated Dashboard tab*

## 5. RACI

| Step | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| PBC extraction & classification | Agent | Manager | Senior | Engagement team |
| Scope/confidentiality approval | Manager/Partner | Partner | Agent | — |
| Standard/Sensitive chase drafts | Agent | Senior | — | Manager |
| Restricted-item handling | Partner | Partner | Senior | Agent (flags only) |
| Escalation | Agent (flags) | Manager | Senior | Partner, Client CFO |
| Non-response memo | Agent (drafts) | Partner | Manager | Engagement file |
| Data-privacy blocked draft | Agent (blocks) | Manager | IT/Privacy contact if firm has one | Senior |
| Dispute adjudication | Manager | Manager | Senior, Partner (if scope-level) | Agent (status only) |
| New component onboarding | Agent (structural setup) | Manager | Partner (materiality/scope) | Engagement team |

## 6. Governing Principles

- Draft-only, always — no email or memo is ever auto-sent
- Confidentiality is a hard gate, not a chase parameter: Restricted items never enter the automated chase pipeline
- Explicit over silent: quality-failed receipts, ambiguous matches, and dependency holds are always logged, never silently resolved
- Multi-entity is the default shape, not an edge case — every schema and view assumes group/component structure
- Version, don't overwrite: every submission is retained; supersession is explicit
- Non-cooperation is an audit-evidence event, not just an admin nuisance — it gets a distinct, documentable output
- Data privacy is a transmission gate, independent of confidentiality: a Sensitive-but-not-Restricted item can still be blocked from plain email if it carries cross-border-restricted personal data — materiality and confidentiality never override this
- Materiality changes urgency, never handling: a below-materiality item gets a slower cadence, not looser confidentiality, privacy, or dependency rules
- A dispute is not a stalled chase: client pushback pauses automation and routes to a human decision, it does not get silently re-chased or silently dropped
- New components join the structure before they join the pipeline: onboarding (contacts, materiality, dependencies) is a prerequisite step, not something inferred on the fly from an incoming file

## 7. Quality Standards

- No chase drafted for an item missing a contact, dependency-held, Restricted, Disputed, or already flagged non-cooperative
- No draft is created, ever, without a data-privacy check passing first — this runs before the confidentiality-tier check, not after
- Every status change timestamped, attributed (agent vs manual), and entity-tagged
- Filename/content matches below confidence threshold always route to manual review, never auto-accept
- No item can reach "Received" status without passing the quality check in Step 8
- A "Rolled Forward — Confirmed No Change" status requires an explicit client representation on file — never inferred from silence or from the passage of time
- Partial sample-based items name the specific outstanding sample references (transaction IDs, employee IDs, SKUs) in Notes — never a generic "partial" with no indication of what's missing

## 8. Post-Delivery Feedback Loop

- Engagement team corrections to mismatches, misclassifications, or dependency errors feed back into that engagement's config (not a global model change)
- Cadence, escalation thresholds, and confidentiality rules are per-engagement configurable

## 9. Cowork Execution Notes

- Gmail connector: draft-creation access only
- Drive connector: needs visibility into client-created (not just agent-created) folders/files across entity subfolders
- Run mode: on-demand initially; scheduled recurring run once cadence is confirmed per engagement
