"""Read/write the contract tables in data/processed/ as Parquet."""

from __future__ import annotations

import pandas as pd

from heatreuse import config
from heatreuse.schemas import TABLES, validate


def table_path(name: str):
    return config.PROCESSED / TABLES[name].filename


def write_table(df: pd.DataFrame, name: str, check: bool = True) -> None:
    """Validate against the contract, then write data/processed/<name>.parquet."""
    if check:
        validate(df, name)
    config.PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_parquet(table_path(name), index=False)


def read_table(name: str, **kwargs) -> pd.DataFrame:
    path = table_path(name)
    if not path.exists():
        owner = TABLES[name].owner
        raise FileNotFoundError(f"{path} not found. It is produced by {owner}; "
                                f"run their step or ask them for the file.")
    return pd.read_parquet(path, **kwargs)
