from datetime import datetime

import pytest

from utils.dates import from_db, to_db, to_display
from utils.validators import cob_after_cone, is_future, is_valid_id, normalize_id


@pytest.mark.parametrize("kind,value", [
    ("CY", "YC006"), ("COB", "COB004"), ("AUTOCONER", "AC-02"), ("DRUM", "D025"),
    ("SPEEDFRAME", "SF-02"), ("SPINDLE", "S128"), ("CY", " yc6 "),
])
def test_valid_ids(kind, value):
    assert is_valid_id(kind, value)


@pytest.mark.parametrize("kind,value", [
    ("CY", ""), ("CY", None), ("CY", "CY006"), ("CY", "YC"), ("COB", "COP004"),
    ("AUTOCONER", "AC02"), ("DRUM", "D-25"), ("SPEEDFRAME", "SF02"),
    ("SPINDLE", "SF-02"), ("SPINDLE", "S12A"),
])
def test_invalid_ids(kind, value):
    assert not is_valid_id(kind, value)


def test_normalize_id():
    assert normalize_id("  cob004 ") == "COB004"
    assert normalize_id(None) == ""


def test_is_future_allows_clock_skew():
    now = datetime(2026, 9, 23, 16, 0, 0)
    assert not is_future(datetime(2026, 9, 23, 16, 4, 59), now)
    assert is_future(datetime(2026, 9, 23, 16, 5, 1), now)


def test_cob_after_cone():
    cone = datetime(2026, 9, 20, 11, 12, 9)
    assert cob_after_cone(datetime(2026, 9, 20, 11, 12, 10), cone)
    assert not cob_after_cone(cone, cone)


def test_date_formats_round_trip():
    dt = datetime(2026, 9, 20, 11, 12, 9)
    assert to_db(dt) == "2026-09-20 11:12:09"
    assert from_db("2026-09-20 11:12:09") == dt
    assert to_display(dt) == "20-09-2026 11:12:09"
    assert to_display(None) == ""
