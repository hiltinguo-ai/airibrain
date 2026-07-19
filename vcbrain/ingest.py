"""Stage 1 - Ingest: normalize a submission folder into a Submission object.

Expected folder layout:
    submission/
        company.json     {company, one_liner, ask}
        deck.md          extracted deck text (any text format works)
        metrics.json     headline metrics as key/value
        revenue.csv      month,revenue  (optional but powers recomputation)
        qa.json          founder Q&A    (optional)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import Submission


def load_submission(folder: str | Path) -> Submission:
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f"Submission folder not found: {folder}")

    meta_path = folder / "company.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    deck_path = folder / "deck.md"
    deck_text = deck_path.read_text() if deck_path.exists() else ""

    metrics_path = folder / "metrics.json"
    metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}

    revenue_series: list[dict] = []
    rev_path = folder / "revenue.csv"
    if rev_path.exists():
        with rev_path.open() as f:
            for row in csv.DictReader(f):
                revenue_series.append(
                    {"month": row["month"].strip(), "revenue": float(row["revenue"])}
                )

    qa_path = folder / "qa.json"
    qa = json.loads(qa_path.read_text()) if qa_path.exists() else {}

    return Submission(
        company=meta.get("company", folder.name),
        one_liner=meta.get("one_liner", ""),
        ask=meta.get("ask", "$100,000"),
        deck_text=deck_text,
        metrics=metrics,
        revenue_series=revenue_series,
        qa=qa,
        source_files=sorted(p.name for p in folder.iterdir() if p.is_file()),
    )
