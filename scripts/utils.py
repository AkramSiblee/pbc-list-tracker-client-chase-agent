"""
utils.py — shared helpers for the PBC List Tracker & Client Chase Agent scripts.
"""
from __future__ import annotations

import datetime as dt
import re


def parse_date(value) -> dt.date | None:
    """Accepts a date, datetime, or YYYY-MM-DD string; returns a date or None."""
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        value = value.strip()
        m = re.match(r"^\d{4}-\d{2}-\d{2}", value)
        if m:
            return dt.date.fromisoformat(m.group(0))
    return None


def add_business_days(start: dt.date, days: int) -> dt.date:
    """Adds N business days (Mon-Fri) to a date. Does not account for holidays —
    holiday calendars are entity/jurisdiction-specific and should be layered in
    by whoever operationalizes this for a live engagement."""
    current = start
    remaining = days
    step = 1 if days >= 0 else -1
    remaining = abs(days)
    while remaining > 0:
        current += dt.timedelta(days=step)
        if current.weekday() < 5:  # Mon-Fri
            remaining -= 1
    return current


def business_days_between(start: dt.date, end: dt.date) -> int:
    """Counts business days strictly between two dates (end - start), signed."""
    if end == start:
        return 0
    step = 1 if end > start else -1
    count = 0
    current = start
    while current != end:
        current += dt.timedelta(days=step)
        if current.weekday() < 5:
            count += step
    return count


def normalize_entity(name: str) -> str:
    """Normalizes entity name variants (e.g. trailing punctuation, casing) so
    matching across files with slightly different spellings still works."""
    if not name:
        return ""
    n = name.strip().rstrip(".")
    return n


CANONICAL_ENTITIES = {
    "meridian global holdings inc": "Meridian Global Holdings Inc.",
    "meridian europe gmbh": "Meridian Europe GmbH",
    "meridian asia pacific pte ltd": "Meridian Asia Pacific Pte Ltd",
    "meridian manufacturing co": "Meridian Manufacturing Co.",
    "meridian nordics ab": "Meridian Nordics AB",
}


def canonical_entity(name: str) -> str | None:
    key = normalize_entity(name).lower().rstrip(".")
    return CANONICAL_ENTITIES.get(key)


ITEM_ID_PATTERN = re.compile(r"\b[A-Z]{2,8}(?:-[A-Z]{2,8}){0,3}-\d{2,3}\b")


def find_item_ids(text: str) -> list[str]:
    """Finds all PBC-style Item IDs in a block of text, e.g. REV-01, PEN-DE-01,
    ITGC-APAC-02, SMP-PAY-DE-01. Order-preserving, de-duplicated."""
    seen = []
    for match in ITEM_ID_PATTERN.finditer(text or ""):
        token = match.group(0)
        if token not in seen:
            seen.append(token)
    return seen
