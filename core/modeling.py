# core/modeling.py

from typing import Dict, Tuple, Optional, Any

import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVC, SVR
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture as GMM

from xgboost import XGBClassifier, XGBRegressor


# ----------------------------------------------------------------------
# Model Factory
# ----------------------------------------------------------------------

def _create_model(
    model_type: str,
    task_type: str,
    random_seed: Optional[int] = None,
    **model_kwargs: Any,
):

    model_type = model_type.lower()
    task_type = task_type.lower()

    # ---------------- Classification ----------------
    if task_type == "classification":

        if model_type == "logistic_regression":
            return LogisticRegression(
                random_state=random_seed,
                max_iter=1000,
                **model_kwargs,
            )

        if model_type == "random_forest":
            return RandomForestClassifier(
                random_state=random_seed,
                **model_kwargs,
            )

        if model_type == "svm":
            return SVC(
                probability=True,
                **model_kwargs,
            )

        if model_type == "xgboost":
            return XGBClassifier(
                random_state=random_seed,
                use_label_encoder=False,
                eval_metric="logloss",
                **model_kwargs,
            )

    # ---------------- Regression ----------------
    if task_type == "regression":

        if model_type == "linear_regression":
            return LinearRegression(**model_kwargs)

        if model_type == "random_forest":
            return RandomForestRegressor(
                random_state=random_seed,
                **model_kwargs,
            )

        if model_type == "svr":
            return SVR(**model_kwargs)

        if model_type == "xgboost":
            return XGBRegressor(
                random_state=random_seed,
                **model_kwargs,
            )

    raise ValueError("Unsupported model_type or task_type.")


# ----------------------------------------------------------------------
# Supervised Training
# ----------------------------------------------------------------------

def train_model(
    df: pd.DataFrame,
    target_column: str,
    task_type: str,
    model_type: str,
    test_size: float = 0.2,
    random_seed: Optional[int] = None,
    **model_kwargs: Any,
):

    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")

    X = df.drop(columns=[target_column])
    y = df[target_column]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_seed,
        stratify=y if task_type == "classification" else None,
    )

    model = _create_model(
        model_type=model_type,
        task_type=task_type,
        random_seed=random_seed,
        **model_kwargs,
    )

    model.fit(X_train, y_train)

    config = {
        "operation": "train_model",
        "task_type": task_type,
        "model_type": model_type,
        "target_column": target_column,
        "random_seed": random_seed,
        "model_params": model_kwargs,
    }

    splits = {
        "X_test": X_test,
        "y_test": y_test,
    }

    return model, splits, config


# ----------------------------------------------------------------------
# PCA
# ----------------------------------------------------------------------

def apply_pca(
    df: pd.DataFrame,
    n_components: int,
    random_seed: Optional[int] = None,
):

    pca = PCA(
        n_components=n_components,
        random_state=random_seed,
    )

    transformed = pca.fit_transform(df)

    pca_df = pd.DataFrame(
        transformed,
        columns=[f"PC{i+1}" for i in range(n_components)],
    )

    config = {
        "operation": "pca",
        "n_components": n_components,
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
    }

    return pca_df, pca, config


# ----------------------------------------------------------------------
# Clustering
# ----------------------------------------------------------------------

def apply_clustering(
    df: pd.DataFrame,
    method: str = "kmeans",
    random_seed: Optional[int] = None,
    **cluster_kwargs,
):

    method = method.lower()

    if method == "kmeans":
        model = KMeans(
            random_state=random_seed,
            **cluster_kwargs,
        )

    elif method == "gmm":
        model = GMM(
            random_state=random_seed,
            **cluster_kwargs)

    else:
        raise ValueError("Unsupported clustering method.")
    labels = model.fit_predict(df)
    result_df = df.copy()
    result_df["cluster"] = labels

    config = {
        "operation": "clustering",
        "method": method,
        "params": cluster_kwargs,
    }

    return {"result": result_df, "labels": labels, "model": model, "config": config}