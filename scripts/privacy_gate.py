"""
privacy_gate.py

Implements the data-privacy hard gate described in docs/skill-workflow.md
Step 7 and docs/io-spec.md Part B8: a Sensitive-but-not-Restricted item can
still be blocked from a plain email attachment if it carries personal data
under a cross-border-restricted regime (e.g., GDPR). This check is orthogonal
to (and runs before) the confidentiality-tier check.

Usage as a library:
    from privacy_gate import check_transmission
    result = check_transmission(entity="Meridian Europe GmbH",
                                 data_type_hint="payroll register",
                                 channel="email_attachment")
    # result.blocked -> True/False, result.reason -> str
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES_PATH = ROOT / "config" / "data_privacy_rules.json"


@dataclass
class PrivacyCheckResult:
    blocked: bool
    reason: str
    required_handling: str | None = None
    matched_rule: dict | None = None


def _load_rules() -> list[dict]:
    return json.loads(RULES_PATH.read_text())


def _matches_data_type(hint: str, rule_data_type: str) -> bool:
    hint_l = hint.lower()
    rule_l = rule_data_type.lower()
    # loose containment match in either direction — config text and free-text
    # hints won't be worded identically ("payroll register" vs "Payroll
    # register / statutory contribution data")
    keywords = [w for w in rule_l.replace("/", " ").split() if len(w) > 3]
    return any(k in hint_l for k in keywords)


def check_transmission(entity: str, data_type_hint: str, channel: str, rules: list[dict] | None = None) -> PrivacyCheckResult:
    """
    entity: canonical entity name (see utils.canonical_entity)
    data_type_hint: free-text description of what's being sent (filename,
        item description, or explicit data-type tag)
    channel: "email_attachment" | "secure_portal" | "sheet_reference" | other
    """
    rules = rules if rules is not None else _load_rules()

    for rule in rules:
        if rule.get("entity") != entity:
            continue
        if rule.get("contains_personal_data") not in ("Yes", "Varies"):
            continue
        if not _matches_data_type(data_type_hint, rule.get("data_type", "")):
            continue

        handling = (rule.get("required_handling") or "").lower()
        # A rule blocks plain email specifically when its handling text says so
        blocks_email = "never attach" in handling or "must be uploaded" in handling or "secure portal only" in handling
        if channel == "email_attachment" and blocks_email:
            return PrivacyCheckResult(
                blocked=True,
                reason=(
                    f"'{data_type_hint}' for {entity} is flagged under {rule.get('applicable_regime')} "
                    f"— cross-border transfer rule: {rule.get('cross_border_transfer_rule')}"
                ),
                required_handling=rule.get("required_handling"),
                matched_rule=rule,
            )
        else:
            return PrivacyCheckResult(
                blocked=False,
                reason=f"Personal data under {rule.get('applicable_regime')}, but channel '{channel}' is permitted.",
                required_handling=rule.get("required_handling"),
                matched_rule=rule,
            )

    return PrivacyCheckResult(blocked=False, reason="No matching data-privacy rule — standard handling applies.")


if __name__ == "__main__":
    # Smoke test against the two Drive_Inbox_Submission_Log.xlsx scenarios this
    # gate is meant to catch/pass — see tests/test_privacy_gate.py for the
    # asserted version of this.
    cases = [
        ("Meridian Europe GmbH", "Lohnbuchhaltung payroll register", "email_attachment"),
        ("Meridian Europe GmbH", "employee census for actuarial valuation", "secure_portal"),
        ("Meridian Asia Pacific Pte Ltd", "employee data listing", "email_attachment"),
        ("Meridian Manufacturing Co.", "employee data", "email_attachment"),
    ]
    for entity, hint, channel in cases:
        r = check_transmission(entity, hint, channel)
        print(f"[{'BLOCKED' if r.blocked else 'ALLOWED'}] {entity} / {hint!r} via {channel}: {r.reason}")
