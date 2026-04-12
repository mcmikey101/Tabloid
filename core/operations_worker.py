"""
Module-level worker functions for operations that can be pickled by multiprocessing.
These are designed to work with Windows multiprocessing which uses spawn mode.
"""

import pandas as pd
from typing import List, Dict, Tuple, Callable, Any, Optional
from core import preprocessing
from core import modeling
from core import evaluation


def apply_single_operation(
    df: pd.DataFrame, 
    operation_id: str,
    config: Dict[str, Any]
) -> Tuple[pd.DataFrame, Dict]:
    """
    Apply a single preprocessing operation to a DataFrame.
    This is a module-level function to ensure it can be pickled.
    
    Args:
        df: Input DataFrame
        operation_id: ID of the operation to apply
        config: Configuration dict for the operation
        
    Returns:
        Tuple of (modified_df, operation_config)
    """
    if operation_id == "handle_missing_values":
        return preprocessing.handle_missing_values(
            df,
            strategy=config.get("strategy", "mean"),
            columns=config.get("columns"),
        )
    elif operation_id == "drop_columns":
        return preprocessing.drop_columns(df, columns=config["columns"])
    elif operation_id == "drop_high_corr_features":
        return preprocessing.drop_high_corr_features(
            df, threshold=config.get("threshold", 0.8)
        )
    elif operation_id == "drop_outliers":
        return preprocessing.drop_outliers(
            df,
            columns=config.get("columns"),
            method=config.get("method", "iqr"),
            threshold=config.get("threshold", 1.5),
        )
    elif operation_id == "standardize":
        return preprocessing.standardize(
            df,
            columns=config.get("columns"),
        )
    elif operation_id == "normalize":
        return preprocessing.normalize(
            df,
            columns=config.get("columns"),
        )
    elif operation_id == "encode_categorical":
        return preprocessing.encode_categorical(
            df,
            columns=config.get("columns"),
            encoding_type=config.get("encoding_type", "label"),
        )
    elif operation_id == "feature_selection":
        return preprocessing.feature_selection(
            df,
            columns=config.get("columns"),
            method=config.get("method", "variance"),
            n_components=config.get("n_components", 2),
        )
    elif operation_id == "dimensionality_reduction":
        return preprocessing.dimensionality_reduction(
            df,
            columns=config["columns"],
            method=config.get("method", "pca"),
            n_components=config.get("n_components", 2),
        )
    else:
        raise ValueError(f"Unknown operation: {operation_id}")


def run_preview_operations(
    input_df: pd.DataFrame,
    operations_sequence: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    Run a sequence of operations for preview.
    This is a module-level function to ensure it can be pickled.
    
    Args:
        input_df: Input DataFrame
        operations_sequence: List of operations to apply
        
    Returns:
        DataFrame after all operations
    """
    preview_df = input_df.copy()
    for op in operations_sequence:
        preview_df, _ = apply_single_operation(
            preview_df,
            op["operation"],
            op["config"]
        )
    return preview_df


def run_operations_and_collect_config(
    input_df: pd.DataFrame,
    operations_sequence: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Run all operations sequentially and collect their configurations.
    This is a module-level function to ensure it can be pickled.
    
    Args:
        input_df: Input DataFrame
        operations_sequence: List of operations to apply
        
    Returns:
        Tuple of (result_df, operations_configs)
    """
    result_df = input_df.copy()
    operations_configs = []

    for op in operations_sequence:
        result_df, config = apply_single_operation(
            result_df,
            op["operation"],
            op["config"]
        )
        operations_configs.append(config)

    return result_df, operations_configs


def run_ml_training(training_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run ML model training in a worker process.
    This is a module-level function to ensure it can be pickled.
    
    Args:
        training_params: Dictionary containing:
            - df: DataFrame to train on
            - task: "Classification", "Regression", or "Clustering"
            - model: Model name (e.g., "Random_Forest", "KMeans")
            - target_col: Target column name (optional for clustering)
            - selected_features: List of features to use (optional)
            - test_size: Test split size
            - random_seed: Random seed
            - **model_kwargs: Model-specific hyperparameters
            
    Returns:
        Dictionary with training results including model, metrics, etc.
    """
    df = training_params["df"]
    task = training_params["task"]
    model = training_params["model"]
    target_col = training_params.get("target_col")
    selected_features = training_params.get("selected_features")
    test_size = training_params.get("test_size", 0.2)
    random_seed = training_params.get("random_seed", 42)
    
    # Extract model-specific kwargs
    model_kwargs = {k: v for k, v in training_params.items() 
                   if k not in ["df", "task", "model", "target_col", "selected_features", 
                               "test_size", "random_seed"]}
    
    # Prepare dataframe with selected features
    if selected_features is not None and task != "Clustering":
        # For supervised learning, use selected features + target
        cols_to_use = list(selected_features) + [target_col]
        df = df[cols_to_use]
    elif selected_features is not None and task == "Clustering":
        # For clustering, use only selected features
        df = df[selected_features]
    
    results = {}
    
    if task == "Clustering":
        if model == "KMeans":
            clustering_results = modeling.apply_clustering(
                df,
                method="kmeans",
                random_seed=random_seed,
                **{k: v for k, v in model_kwargs.items() if k.startswith("kmeans_")}
            )
            labels = clustering_results["labels"]
            results["model"] = clustering_results["model"]
            results["df"] = clustering_results["result"]
            results["labels"] = labels
            results["task"] = task
            results["model_name"] = model
            metrics = {"silhouette_score": evaluation.evaluate_clustering(
                clustering_results["result"], labels
            )}
            results["metrics"] = metrics
        elif model == "GMM":
            clustering_results = modeling.apply_clustering(
                df,
                method="gmm",
                random_seed=random_seed,
                **{k: v for k, v in model_kwargs.items() if k.startswith("gmm_")}
            )
            labels = clustering_results["labels"]
            results["model"] = clustering_results["model"]
            results["df"] = clustering_results["result"]
            results["labels"] = labels
            results["task"] = task
            results["model_name"] = model
            metrics = {"silhouette_score": evaluation.evaluate_clustering(
                clustering_results["result"], labels
            )}
            results["metrics"] = metrics
    else:
        model_type = model.lower()
        task_type = task.lower()
        
        current_model, current_splits, config = modeling.train_model(
            df=df,
            target_column=target_col,
            task_type=task_type,
            model_type=model_type,
            test_size=test_size,
            random_seed=random_seed,
            **model_kwargs
        )
        
        if task_type == "classification":
            metrics = evaluation.evaluate_classification(
                current_model,
                current_splits["X_test"],
                current_splits["y_test"]
            )
        else:
            metrics = evaluation.evaluate_regression(
                current_model,
                current_splits["X_test"],
                current_splits["y_test"]
            )
        
        results["model"] = current_model
        results["splits"] = current_splits
        results["config"] = config
        results["metrics"] = metrics
        results["task"] = task
        results["model_name"] = model
    
    return results
