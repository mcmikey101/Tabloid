# core/preprocessing.py

from typing import Dict, List, Tuple, Optional
import math

import numpy as np

import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

try:
    import umap
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False


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

            if strategy in {"mean", "median"} and not pd.api.types.is_numeric_dtype(df_copy[col]):
                mode_values = df_copy[col].mode(dropna=True)
                value = mode_values.iloc[0] if not mode_values.empty else None
            elif strategy == "mean":
                value = df_copy[col].mean()
            elif strategy == "median":
                value = df_copy[col].median()
            elif strategy == "mode":
                mode_values = df_copy[col].mode(dropna=True)
                value = mode_values.iloc[0] if not mode_values.empty else None
            else:
                raise ValueError("Неподдерживаемая стратегия обработки пропусков.")

            if value is not None:
                df_copy[col] = df_copy[col].fillna(value)

    config = {
        "operation": "handle_missing_values",
        "strategy": strategy,
        "columns": columns,
    }

    return df_copy, config


# drop outliers

def drop_outliers(df: pd.DataFrame, columns: list = None, method: str = "iqr", threshold: float = 1.5):
    """
    Drop rows containing outliers in specified columns.
    
    Args:
        df: Input dataframe
        columns: List of columns to check for outliers. If None, uses all numeric columns
        method: Method for outlier detection ("iqr" or "zscore")
        threshold: IQR multiplier (1.5) or zscore threshold (3)
    
    Returns:
        df_copy: DataFrame with outliers removed
        config: Configuration dictionary
    """
    df_copy = df.copy()
    
    if columns is None:
        columns = df_copy.select_dtypes(include=['number']).columns.tolist()
    
    rows_before = len(df_copy)
    
    if method == "iqr":
        # Build mask for all columns at once to avoid multiple filter operations
        mask = pd.Series([True] * len(df_copy), index=df_copy.index)
        for col in columns:
            if col in df_copy.columns:
                Q1 = df_copy[col].quantile(0.25)
                Q3 = df_copy[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                col_mask = (df_copy[col] >= lower_bound) & (df_copy[col] <= upper_bound)
                mask &= col_mask
        df_copy = df_copy[mask]
    
    elif method == "zscore":
        from scipy import stats
        # Build mask for all columns at once
        mask = pd.Series([True] * len(df_copy), index=df_copy.index)
        for col in columns:
            if col in df_copy.columns:
                # Handle NaN values properly by filling them
                col_filled = df_copy[col].fillna(df_copy[col].mean())
                z_scores = np.abs(stats.zscore(col_filled, nan_policy='propagate'))
                # Treat NaN as outliers (False in mask)
                col_mask = ~np.isnan(z_scores) & (z_scores <= threshold)
                mask &= col_mask
        df_copy = df_copy[mask]
    
    rows_after = len(df_copy)
    
    config = {
        "operation": "drop_outliers",
        "method": method,
        "columns": columns,
        "rows_removed": rows_before - rows_after,
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
    """
    Drop features that have high correlation with each other.
    
    Args:
        df: Input dataframe
        threshold: Correlation threshold for dropping (default 0.8)
    
    Returns:
        DataFrame with highly correlated features removed and config dict
    """
    # Only work with numeric columns
    numeric_df = df.select_dtypes(include=['number'])
    
    if numeric_df.shape[1] == 0:
        # No numeric columns to correlate
        return df.copy(), {
            "operation": "drop_high_corr_features",
            "threshold": threshold,
            "dropped_columns": [],
        }
    
    corr = numeric_df.corr().abs()
    
    # Get upper triangle of correlation matrix (avoid duplicates)
    upper = corr.where(~np.tril(np.ones(corr.shape), k=0).astype(bool))
    
    # Find columns to drop (properly handle NaN values)
    to_drop = []
    for col in upper.columns:
        # Use fillna(False) to treat NaN as non-correlated
        if (upper[col] > threshold).fillna(False).any():
            to_drop.append(col)

    config = {
        "operation": "drop_high_corr_features",
        "threshold": threshold,
        "dropped_columns": to_drop,
    }
    
    return df.drop(columns=to_drop, errors='ignore'), config


# ----------------------------------------------------------------------
# Class Oversampling
# ----------------------------------------------------------------------

def _normalize_class_proportions(
    proportions: Dict,
    classes: List,
) -> Dict:
    normalized = {}
    total = 0.0

    for class_value in classes:
        raw_value = proportions.get(class_value, proportions.get(str(class_value), 0))
        value = float(raw_value)
        if value < 0:
            raise ValueError("Пропорции классов не могут быть отрицательными.")
        normalized[class_value] = value
        total += value

    if total <= 0:
        raise ValueError("Укажите положительную пропорцию хотя бы для одного класса.")

    return {class_value: value / total for class_value, value in normalized.items()}


def _calculate_oversample_targets(
    class_counts: pd.Series,
    target_proportions: Dict,
) -> Dict:
    classes = class_counts.index.tolist()
    proportions = _normalize_class_proportions(target_proportions, classes)

    for class_value in classes:
        if class_counts[class_value] > 0 and proportions[class_value] <= 0:
            raise ValueError(
                f"Для класса '{class_value}' нельзя задать нулевую долю без удаления исходных строк."
            )

    target_total = max(
        math.ceil(class_counts[class_value] / proportions[class_value])
        for class_value in classes
        if proportions[class_value] > 0
    )

    target_counts = {
        class_value: max(
            int(class_counts[class_value]),
            math.ceil(target_total * proportions[class_value]),
        )
        for class_value in classes
    }

    return target_counts


def oversample_classes(
    df: pd.DataFrame,
    class_column: str,
    target_proportions: Dict,
    method: str = "sample",
    synthesis_model: str = "gaussian_copula",
    random_seed: Optional[int] = 42,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Increase class counts to approach target proportions without removing original rows.

    method:
        - "sample": duplicate rows from the original dataset with replacement
        - "synthesis": generate additional rows per class using core.synthesis
    """
    if class_column not in df.columns:
        raise ValueError(f"Столбец класса '{class_column}' не найден.")

    if df.empty:
        raise ValueError("DataFrame пуст.")

    method = method.lower()
    if method not in {"sample", "synthesis"}:
        raise ValueError("Метод oversample должен быть 'sample' или 'synthesis'.")

    df_copy = df.copy()
    class_counts = df_copy[class_column].value_counts(dropna=False)
    if len(class_counts) < 2:
        raise ValueError("Для oversample нужно минимум два класса.")

    target_counts = _calculate_oversample_targets(class_counts, target_proportions)
    generated_parts = [df_copy]
    rows_added_by_class = {}

    for class_value, current_count in class_counts.items():
        rows_to_add = target_counts[class_value] - int(current_count)
        rows_added_by_class[str(class_value)] = rows_to_add

        if rows_to_add <= 0:
            continue

        class_df = df_copy[df_copy[class_column] == class_value]

        if method == "sample":
            sampled = class_df.sample(
                n=rows_to_add,
                replace=True,
                random_state=random_seed,
            )
            generated_parts.append(sampled)
        else:
            if len(class_df) < 2:
                raise ValueError(
                    f"Для синтетического oversample класса '{class_value}' нужно минимум 2 строки."
                )
            from core import synthesis

            synthetic_df, _ = synthesis.synthesize(
                df=class_df.reset_index(drop=True),
                num_rows=rows_to_add,
                model_type=synthesis_model,
                evaluate=False,
            )
            synthetic_df[class_column] = class_value
            generated_parts.append(synthetic_df[df_copy.columns])

    result_df = pd.concat(generated_parts, ignore_index=True)

    config = {
        "operation": "oversample_classes",
        "class_column": class_column,
        "method": method,
        "synthesis_model": synthesis_model if method == "synthesis" else None,
        "target_proportions": {
            str(key): float(value) for key, value in target_proportions.items()
        },
        "original_counts": {str(key): int(value) for key, value in class_counts.items()},
        "target_counts": {str(key): int(value) for key, value in target_counts.items()},
        "rows_added_by_class": rows_added_by_class,
        "rows_before": len(df_copy),
        "rows_after": len(result_df),
    }

    return result_df, config


# ----------------------------------------------------------------------
# Standard Scaling
# ----------------------------------------------------------------------

def standard_scale(
    df: pd.DataFrame,
    columns: List[str],
) -> Tuple[pd.DataFrame, Dict]:
    df_copy = df.copy()
    
    # Filter to only existing columns
    existing_columns = [col for col in columns if col in df_copy.columns]
    
    if not existing_columns:
        raise ValueError(f"Ни один из указанных столбцов {columns} не найден в датафрейме.")
    
    if len(existing_columns) < len(columns):
        missing = [col for col in columns if col not in df_copy.columns]
        print(f"Предупреждение: столбцы {missing} не найдены в датафрейме. Масштабируются только существующие столбцы.")
    
    scaler = StandardScaler()
    # Preserve index when transforming
    scaled_values = scaler.fit_transform(df_copy[existing_columns])
    df_copy[existing_columns] = scaled_values

    config = {
        "operation": "standard_scale",
        "columns": existing_columns,
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
    
    # Filter to only existing columns
    existing_columns = [col for col in columns if col in df_copy.columns]
    
    if not existing_columns:
        raise ValueError(f"Ни один из указанных столбцов {columns} не найден в датафрейме.")
    
    if len(existing_columns) < len(columns):
        missing = [col for col in columns if col not in df_copy.columns]
        print(f"Предупреждение: столбцы {missing} не найдены в датафрейме. Масштабируются только существующие столбцы.")
    
    scaler = MinMaxScaler()
    # Preserve index when transforming
    scaled_values = scaler.fit_transform(df_copy[existing_columns])
    df_copy[existing_columns] = scaled_values

    config = {
        "operation": "minmax_scale",
        "columns": existing_columns,
    }

    return df_copy, config


def robust_scale(
    df: pd.DataFrame,
    columns: List[str],
) -> Tuple[pd.DataFrame, Dict]:
    """
    Scale features using robust methods resistant to outliers.
    Uses median and interquartile range instead of mean and std.
    
    Args:
        df: Input dataframe
        columns: List of columns to scale
    
    Returns:
        Scaled dataframe and config dict
    """
    df_copy = df.copy()
    
    # Filter to only existing columns
    existing_columns = [col for col in columns if col in df_copy.columns]
    
    if not existing_columns:
        raise ValueError(f"Ни один из указанных столбцов {columns} не найден в датафрейме.")
    
    if len(existing_columns) < len(columns):
        missing = [col for col in columns if col not in df_copy.columns]
        print(f"Предупреждение: столбцы {missing} не найдены в датафрейме. Масштабируются только существующие столбцы.")
    
    scaler = RobustScaler()
    # Preserve index when transforming
    scaled_values = scaler.fit_transform(df_copy[existing_columns])
    df_copy[existing_columns] = scaled_values

    config = {
        "operation": "robust_scale",
        "columns": existing_columns,
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
        raise ValueError(f"Столбец '{column}' не найден.")

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


# ----------------------------------------------------------------------
# Dimensionality Reduction
# ----------------------------------------------------------------------

def reduce_dimensionality(
    df: pd.DataFrame,
    columns: List[str],
    method: str = "pca",
    n_components: int = 2,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Reduce dimensionality of numerical features using PCA, t-SNE, or UMAP.
    
    Args:
        df: Input dataframe
        columns: List of numerical columns to reduce
        method: Dimensionality reduction method ("pca", "tsne", or "umap")
        n_components: Number of dimensions to reduce to
    
    Returns:
        - Transformed DataFrame with original data + new reduced dimensions
        - Config containing operation details
    """
    
    df_copy = df.copy()
    
    # Filter to only existing columns
    existing_columns = [col for col in columns if col in df_copy.columns]
    
    if not existing_columns:
        raise ValueError(f"Ни один из указанных столбцов {columns} не найден в датафрейме.")
    
    # Select only numerical data
    numerical_cols = df_copy[existing_columns].select_dtypes(include=[np.number]).columns.tolist()
    
    if not numerical_cols:
        raise ValueError(f"Ни один из выбранных столбцов {existing_columns} не содержит числовых данных.")
    
    if len(numerical_cols) < n_components:
        raise ValueError(
            f"Количество компонент ({n_components}) не может превышать число признаков ({len(numerical_cols)})."
        )
    
    if n_components < 1:
        raise ValueError("n_components должно быть не меньше 1.")
    
    # Prepare data for dimensionality reduction
    X = df_copy[numerical_cols].values
    
    # Apply the selected method
    if method.lower() == "pca":
        reducer = PCA(n_components=n_components, random_state=42)
        reduced = reducer.fit_transform(X)
        explained_variance = reducer.explained_variance_ratio_.tolist()
    elif method.lower() == "tsne":
        reducer = TSNE(n_components=n_components, random_state=42, verbose=0)
        reduced = reducer.fit_transform(X)
        explained_variance = None
    elif method.lower() == "umap":
        if not HAS_UMAP:
            raise RuntimeError("UMAP не установлен. Установите его командой: pip install umap-learn")
        reducer = umap.UMAP(n_components=n_components, random_state=42)
        reduced = reducer.fit_transform(X)
        explained_variance = None
    else:
        raise ValueError(f"Неизвестный метод снижения размерности: {method}")
    
    # Create new column names for reduced dimensions
    prefix = method.lower()
    new_columns = [f"{prefix}_{i+1}" for i in range(n_components)]
    
    # Add reduced dimensions as new columns
    for i, col_name in enumerate(new_columns):
        df_copy[col_name] = reduced[:, i]
    
    # Remove the original columns that were reduced
    df_copy = df_copy.drop(columns=numerical_cols)
    
    config = {
        "operation": "reduce_dimensionality",
        "method": method.lower(),
        "original_columns": numerical_cols,
        "n_components": n_components,
        "new_columns": new_columns,
        "explained_variance": explained_variance,
    }
    
    return df_copy, config
