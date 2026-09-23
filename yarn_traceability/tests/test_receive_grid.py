from datetime import datetime

import pandas as pd

from services.receive_service import CobEntry, ValidationError
from ui.receive import GRID_COLUMNS, format_errors, grid_to_entries


def test_grid_to_entries_skips_blank_rows_and_converts_times():
    df = pd.DataFrame({
        "COB ID": ["cob900", None],
        "Speedframe": ["SF-01", None],
        "Spindle": ["S101", None],
        "Scan date & time": [pd.Timestamp("2026-09-23 10:00:00.5"), pd.NaT],
    }, columns=GRID_COLUMNS)
    assert grid_to_entries(df) == [CobEntry("cob900", "SF-01", "S101", datetime(2026, 9, 23, 10, 0, 0))]


def test_grid_row_without_time_or_spindle():
    df = pd.DataFrame({"COB ID": ["COB900"], "Speedframe": ["SF-01"], "Spindle": [None],
                       "Scan date & time": [pd.NaT]}, columns=GRID_COLUMNS)
    assert grid_to_entries(df) == [CobEntry("COB900", "SF-01", "", None)]


def test_format_errors_groups_cone_and_rows():
    text = format_errors([
        ValidationError("cy_id", None, "Yarn Cone ID is required"),
        ValidationError("spindle_id", 2, "Spindle S210 belongs to SF-05, not SF-01"),
    ])
    assert text == ("- **Yarn Cone:** Yarn Cone ID is required\n"
                    "- **COB row 2:** Spindle S210 belongs to SF-05, not SF-01")
