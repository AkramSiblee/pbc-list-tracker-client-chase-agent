from privacy_gate import check_transmission


def test_gdpr_blocks_german_payroll_email_attachment():
    result = check_transmission("Meridian Europe GmbH", "Lohnbuchhaltung payroll register", "email_attachment")
    assert result.blocked is True
    assert "GDPR" in result.reason


def test_gdpr_allows_secure_portal_channel():
    result = check_transmission("Meridian Europe GmbH", "employee census for actuarial valuation", "secure_portal")
    assert result.blocked is False


def test_singapore_pdpa_allows_email_per_existing_safeguards():
    result = check_transmission("Meridian Asia Pacific Pte Ltd", "employee data listing", "email_attachment")
    assert result.blocked is False


def test_canada_pipeda_allows_email_per_existing_agreement():
    result = check_transmission("Meridian Manufacturing Co.", "employee data", "email_attachment")
    assert result.blocked is False


def test_non_personal_data_item_has_no_matching_rule():
    result = check_transmission("Meridian Asia Pacific Pte Ltd", "inventory count listing", "email_attachment")
    assert result.blocked is False


def test_sensitive_not_restricted_still_blocked_for_gdpr_data():
    """The core point of this gate: confidentiality tier and data-privacy are
    orthogonal. This item is only 'Sensitive', not 'Restricted', yet must
    still be blocked on the email channel."""
    result = check_transmission("Meridian Europe GmbH", "payroll register", "email_attachment")
    assert result.blocked is True
