"""Shared helpers for the NEM generator behaviour project."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine


START_DATE = "2026-02-01"
END_DATE = "2026-03-01"
REGIONS = ["NSW1", "VIC1"]


def project_root() -> Path:
    root = Path.cwd()
    return root.parent if root.name == "notebooks" else root


def output_paths() -> tuple[Path, Path, Path]:
    root = project_root()
    csv = root / "outputs" / "csv"
    charts = root / "outputs" / "charts"
    reports = root / "outputs" / "reports"
    for path in [csv, charts, reports]:
        path.mkdir(parents=True, exist_ok=True)
    return csv, charts, reports


def get_engine_from_env():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("Set DATABASE_URL, for example postgresql+psycopg2://user:password@host:5432/dbname")
    return create_engine(database_url)


def save_csv(df: pd.DataFrame, filename: str) -> Path:
    csv_dir, _, _ = output_paths()
    path = csv_dir / filename
    df.to_csv(path, index=False)
    return path
