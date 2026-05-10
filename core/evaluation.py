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
    silhouette_score,
    confusion_matrix,
    roc_curve,
    auc
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


# ----------------------------------------------------------------------
# Confusion Matrix and ROC Curve
# ----------------------------------------------------------------------

def get_confusion_matrix(
    model,
    X_test,
    y_test,
) -> Dict[str, Any]:
    """Generate confusion matrix data for classification models."""
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred)
    
    # Get unique classes from y_test
    classes = np.unique(y_test)
    
    return {
        "confusion_matrix": cm,
        "classes": classes,
        "y_pred": y_pred,
        "y_test": y_test,
    }


def get_roc_curve_data(
    model,
    X_test,
    y_test,
) -> Dict[str, Any]:
    """Generate ROC curve data for binary and multi-class classification."""
    roc_data = {}
    
    if not hasattr(model, "predict_proba"):
        return roc_data
    
    y_pred_proba = model.predict_proba(X_test)
    classes = model.classes_
    
    # For binary classification
    if len(classes) == 2:
        fpr, tpr, _ = roc_curve(y_test, y_pred_proba[:, 1])
        roc_auc = auc(fpr, tpr)
        roc_data["binary"] = {
            "fpr": fpr,
            "tpr": tpr,
            "auc": roc_auc,
            "class": classes[1]
        }
    else:
        # For multi-class, use One-vs-Rest approach
        from sklearn.preprocessing import label_binarize
        y_test_bin = label_binarize(y_test, classes=classes)
        
        for i, class_label in enumerate(classes):
            fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_pred_proba[:, i])
            roc_auc = auc(fpr, tpr)
            roc_data[str(i)] = {
                "fpr": fpr,
                "tpr": tpr,
                "auc": roc_auc,
                "class": class_label
            }
    
    return roc_data