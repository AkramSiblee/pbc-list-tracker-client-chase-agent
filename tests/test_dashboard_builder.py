from dashboard_builder import build_dashboard


ITEMS = [
    {"item_id": "REV-01", "entity": "Meridian Global Holdings Inc.", "phase": "Interim",
     "materiality_tier": "Above Performance Materiality", "status": "Received"},
    {"item_id": "PPE-01", "entity": "Meridian Global Holdings Inc.", "phase": "Final",
     "materiality_tier": "Above Performance Materiality", "status": "Overdue"},
    {"item_id": "PPE-CA-01", "entity": "Meridian Manufacturing Co.", "phase": "Final",
     "materiality_tier": "Below Performance Materiality", "status": "Overdue"},
    {"item_id": "RPT-04", "entity": "Meridian Manufacturing Co.", "phase": "Final",
     "materiality_tier": "Specific-Risk (Regardless of Materiality)",
     "status": "Disputed — Pending Manager Adjudication"},
    {"item_id": "PEN-DE-01", "entity": "Meridian Europe GmbH", "phase": "Final",
     "materiality_tier": "Above Performance Materiality", "status": "Requested",
     "vendor_specialist": "Hoffmann Versicherungsmathematik GmbH"},
]


def test_group_rollup_counts():
    dash = build_dashboard(ITEMS)
    assert dash["group_rollup"]["total"] == 5
    assert dash["group_rollup"]["complete"] == 1
    assert dash["group_rollup"]["pct_complete"] == 20.0


def test_per_entity_rollup_isolates_components():
    dash = build_dashboard(ITEMS)
    mfg = dash["per_entity"]["Meridian Manufacturing Co."]
    assert mfg["total"] == 2
    assert mfg["disputed"] == 1


def test_materiality_weighted_overdue_separates_tiers():
    dash = build_dashboard(ITEMS)
    overdue_by_tier = dash["materiality_weighted_overdue"]
    assert overdue_by_tier.get("Above Performance Materiality") == 1
    assert overdue_by_tier.get("Below Performance Materiality") == 1


def test_vendor_specialist_lane_isolated():
    dash = build_dashboard(ITEMS)
    assert "Meridian Europe GmbH" in dash["vendor_specialist_lane"]
    assert dash["vendor_specialist_lane"]["Meridian Europe GmbH"]["total"] == 1


def test_disputed_lane_lists_item_ids():
    dash = build_dashboard(ITEMS)
    assert dash["disputed_lane"] == ["RPT-04"]


def test_data_privacy_exceptions_lane_passthrough():
    dash = build_dashboard(ITEMS, blocked_draft_count=3)
    assert dash["data_privacy_exceptions_lane"]["blocked_draft_count"] == 3
