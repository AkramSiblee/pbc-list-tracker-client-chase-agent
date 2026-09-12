# Client System Requirements — PBC List Tracker & Client Chase Agent

What needs to be on a machine before this agent will run, from a bare
install through a passing test suite.

## A. To run Claude Code at all (required)

| Item | Requirement |
|---|---|
| OS | Windows 10/11, macOS, or Linux |
| Claude access | Pro/Max subscription, or Anthropic API credits |
| Node.js | v18+ (needed to install the Claude Code CLI) |
| Claude Code CLI | `npm install -g @anthropic-ai/claude-code` |
| Terminal | PowerShell (built into Windows) or Terminal/bash (macOS/Linux) — nothing to install |
| Editor (optional) | VS Code — not required, but makes reviewing diffs/tracker/drafts easier |

## B. To run the PBC pipeline (required)

| Item | Requirement |
|---|---|
| Python | 3.9+ |
| Python packages | `openpyxl`, `pdfplumber`, `pytest` — via `pip install -r requirements.txt` |
| pandoc | On PATH, not pip-installable — parses the `.docx` audit programs |
| Git | Recommended (not currently initialized in this folder) — gives config/extraction changes a reviewable audit trail |

## C. Not required yet — pending an integration decision

| Item | Requirement |
|---|---|
| Google Workspace access | Gmail (draft-only) + Drive visibility into client folders — only needed once live chase/monitor runs |
| MCP servers or Google OAuth app | Per `CLAUDE.md`'s "Integration decision not yet made" — needed before `run-pbc-chase` touches real Gmail/Drive |

## First run — verify it works (in order)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/generate_config.py
python scripts/extract_pbc_items.py
python scripts/build_master_tracker.py
python scripts/match_submissions.py
python -m pytest tests/ -v   # expect 48 passing
```
