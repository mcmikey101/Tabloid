# core/preprocessing.py

from typing import Dict, List, Tuple, Optional

import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler


# ----------------------------------------------------------------------
# Missing Values
# ----------------------------------------------------------------------

def handle_missing_values(
    df: pd.DataFrame,
    strategy: str = "mean",
    columns: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Handle missing values using a simple strategy.

    strategy:
        - "mean"
        - "median"
        - "mode"
        - "drop_rows"
        - "drop_columns"
    """

    df_copy = df.copy()
    columns = columns or df_copy.columns.tolist()

    if strategy == "drop_rows":
        df_copy = df_copy.dropna()
    elif strategy == "drop_columns":
        df_copy = df_copy.dropna(axis=1)
    else:
        for col in columns:
            if col not in df_copy.columns:
                continue

            if strategy == "mean":
                value = df_copy[col].mean()
            elif strategy == "median":
                value = df_copy[col].median()
            elif strategy == "mode":
                value = df_copy[col].mode().iloc[0] if not df_copy[col].mode().empty else None
            else:
                raise ValueError("Unsupported missing value strategy.")

            df_copy[col] = df_copy[col].fillna(value)

    config = {
        "operation": "handle_missing_values",
        "strategy": strategy,
        "columns": columns,
    }

    return df_copy, config


# ----------------------------------------------------------------------
# Drop Columns
# ----------------------------------------------------------------------

def drop_columns(
    df: pd.DataFrame,
    columns: List[str],
) -> Tuple[pd.DataFrame, Dict]:
    df_copy = df.copy()
    df_copy = df_copy.drop(columns=columns, errors="ignore")

    config = {
        "operation": "drop_columns",
        "columns": columns,
    }

    return df_copy, config

def drop_high_corr_features(df, threshold=0.8):
    corr = df.corr(numeric_only=True).abs()
    upper = corr.where(~pd.np.tril(pd.np.ones(corr.shape)).astype(bool))
    
    to_drop = [col for col in upper.columns if any(upper[col] > threshold)]

    config = {
        "operation": "drop_high_corr_features",
        "threshold": threshold,
        "dropped_columns": to_drop,
    }
    
    return df.drop(columns=to_drop), config


# ----------------------------------------------------------------------
# Standard Scaling
# ----------------------------------------------------------------------

def standard_scale(
    df: pd.DataFrame,
    columns: List[str],
) -> Tuple[pd.DataFrame, Dict]:
    df_copy = df.copy()
    scaler = StandardScaler()

    df_copy[columns] = scaler.fit_transform(df_copy[columns])

    config = {
        "operation": "standard_scale",
        "columns": columns,
    }

    return df_copy, config


# ----------------------------------------------------------------------
# Min-Max Scaling
# ----------------------------------------------------------------------

def minmax_scale(
    df: pd.DataFrame,
    columns: List[str],
) -> Tuple[pd.DataFrame, Dict]:
    df_copy = df.copy()
    scaler = MinMaxScaler()

    df_copy[columns] = scaler.fit_transform(df_copy[columns])

    config = {
        "operation": "minmax_scale",
        "columns": columns,
    }

    return df_copy, config


# ----------------------------------------------------------------------
# One-Hot Encoding
# ----------------------------------------------------------------------

def one_hot_encode(
    df: pd.DataFrame,
    columns: List[str],
    drop_first: bool = False,
) -> Tuple[pd.DataFrame, Dict]:
    df_copy = df.copy()

    df_copy = pd.get_dummies(
        df_copy,
        columns=columns,
        drop_first=drop_first,
        dtype=int,
    )

    config = {
        "operation": "one_hot_encode",
        "columns": columns,
        "drop_first": drop_first,
    }

    return df_copy, config

def encode_classes(
    df: pd.DataFrame,
    column: str,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Encode categorical class labels in a column into integers.

    Returns:
        - Transformed DataFrame
        - Config containing mapping
    """

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")

    df_copy = df.copy()

    categories = df_copy[column].astype("category").cat.categories.tolist()

    mapping = {category: idx for idx, category in enumerate(categories)}

    df_copy[column] = df_copy[column].map(mapping)

    config = {
        "operation": "encode_classes",
        "column": column,
        "mapping": mapping,
    }

    return df_copy, config