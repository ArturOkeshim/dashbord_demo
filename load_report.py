"""Load turnover sheet from report_for_web.xlsx."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"line", "obj", "item", "date", "debet"}
DEFAULT_REPORT = Path(__file__).resolve().parent / "report_for_web.xlsx"
KNOWN_LINES = ("50.01", "50.02", "51")


def _normalize_line(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return format(value, "g")
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].replace(".", "", 1).isdigit():
        return text[:-2]
    return text


def _find_turnover_sheet(path: Path) -> str:
    book = pd.ExcelFile(path)
    for sheet in book.sheet_names:
        frame = pd.read_excel(book, sheet_name=sheet, nrows=5)
        if REQUIRED_COLUMNS.issubset(set(frame.columns)):
            return sheet
    raise ValueError(
        f"No sheet with columns {sorted(REQUIRED_COLUMNS)} found in {path}"
    )


def load_turnover(path: Path | str = DEFAULT_REPORT) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {path}")

    sheet = _find_turnover_sheet(path)
    frame = pd.read_excel(path, sheet_name=sheet)

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["debet"] = pd.to_numeric(frame["debet"], errors="coerce")
    frame["line"] = frame["line"].map(_normalize_line)
    frame["obj"] = frame["obj"].astype(str).str.strip()
    frame["item"] = frame["item"].astype(str).str.strip()

    frame = frame.dropna(subset=["date", "debet"])
    frame = frame[frame["debet"] > 0]
    return frame.reset_index(drop=True)
