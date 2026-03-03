# core/metadata.py

from typing import Dict, Any
import pandas as pd


def _numeric_summary(series: pd.Series) -> Dict[str, Any]:
    desc = series.describe()

    return {
        "dtype": str(series.dtype),
        "count": int(desc.get("count", 0)),
        "missing": int(series.isna().sum()),
        "missing_pct": float(series.isna().mean()),
        "mean": float(desc.get("mean")) if "mean" in desc else None,
        "std": float(desc.get("std")) if "std" in desc else None,
        "min": float(desc.get("min")) if "min" in desc else None,
        "25%": float(desc.get("25%")) if "25%" in desc else None,
        "50%": float(desc.get("50%")) if "50%" in desc else None,
        "75%": float(desc.get("75%")) if "75%" in desc else None,
        "max": float(desc.get("max")) if "max" in desc else None,
        "unique": int(series.nunique(dropna=True)),
    }


def _categorical_summary(series: pd.Series) -> Dict[str, Any]:
    value_counts = series.value_counts(dropna=True)

    top_values = (
        value_counts.head(10).to_dict()
        if not value_counts.empty
        else {}
    )

    return {
        "dtype": str(series.dtype),
        "count": int(series.count()),
        "missing": int(series.isna().sum()),
        "missing_pct": float(series.isna().mean()),
        "unique": int(series.nunique(dropna=True)),
        "top_values": top_values,
    }


def _boolean_summary(series: pd.Series) -> Dict[str, Any]:
    value_counts = series.value_counts(dropna=True).to_dict()

    return {
        "dtype": str(series.dtype),
        "count": int(series.count()),
        "missing": int(series.isna().sum()),
        "missing_pct": float(series.isna().mean()),
        "unique": int(series.nunique(dropna=True)),
        "distribution": value_counts,
    }


def _datetime_summary(series: pd.Series) -> Dict[str, Any]:
    return {
        "dtype": str(series.dtype),
        "count": int(series.count()),
        "missing": int(series.isna().sum()),
        "missing_pct": float(series.isna().mean()),
        "min": series.min().isoformat() if series.notna().any() else None,
        "max": series.max().isoformat() if series.notna().any() else None,
        "unique": int(series.nunique(dropna=True)),
    }


def derive_metadata(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Derive descriptive statistics and structural metadata from a dataset.
    """

    metadata: Dict[str, Any] = {
        "num_rows": int(df.shape[0]),
        "num_columns": int(df.shape[1]),
        "memory_usage_bytes": int(df.memory_usage(deep=True).sum()),
        "columns": {},
    }

    for col in df.columns:
        series = df[col]

        if pd.api.types.is_numeric_dtype(series):
            metadata["columns"][col] = _numeric_summary(series)

        elif pd.api.types.is_bool_dtype(series):
            metadata["columns"][col] = _boolean_summary(series)

        elif pd.api.types.is_datetime64_any_dtype(series):
            metadata["columns"][col] = _datetime_summary(series)

        else:
            metadata["columns"][col] = _categorical_summary(series)

    return metadata