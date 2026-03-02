# core/evaluation.py

from typing import Dict, Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    silhouette_score
)


# ----------------------------------------------------------------------
# Classification Evaluation
# ----------------------------------------------------------------------

def evaluate_classification(
    model,
    X_test,
    y_test,
) -> Dict[str, Any]:

    y_pred = model.predict(X_test)

    results = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, average="weighted", zero_division=0),
        "recall": recall_score(y_test, y_pred, average="weighted", zero_division=0),
        "f1_score": f1_score(y_test, y_pred, average="weighted", zero_division=0),
    }

    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_test)

        if y_prob.shape[1] == 2:
            results["roc_auc"] = roc_auc_score(y_test, y_prob[:, 1])
        else:
            results["roc_auc"] = roc_auc_score(
                y_test,
                y_prob,
                multi_class="ovr",
            )

    return results


# ----------------------------------------------------------------------
# Regression Evaluation
# ----------------------------------------------------------------------

def evaluate_regression(
    model,
    X_test,
    y_test,
) -> Dict[str, Any]:

    y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)

    results = {
        "mse": mse,
        "rmse": np.sqrt(mse),
        "mae": mean_absolute_error(y_test, y_pred),
        "r2": r2_score(y_test, y_pred),
    }

    return results

def evaluate_clustering(
    df,
    labels,
):

    score = silhouette_score(df, labels)

    return {
        "silhouette_score": score,
    }