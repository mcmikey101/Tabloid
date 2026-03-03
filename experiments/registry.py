# core/experiments.py

from __future__ import annotations
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import uuid
import pickle


class ExperimentManager:
    """
    Tracks ML experiments so they can be fully recreated later.

    Stores:
    - dataset name
    - dataset version
    - preprocessing config
    - model type
    - hyperparameters
    - metrics
    - random seed
    - timestamp
    - optional serialized model artifact
    """

    def __init__(self, base_path: str | Path = "experiments"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        dataset_name: str,
        dataset_version: str,
        model_type: str,
        hyperparameters: Dict[str, Any],
        metrics: Dict[str, Any],
        preprocessing_config: Optional[Dict[str, Any]] = None,
        random_seed: Optional[int] = None,
        model_object: Optional[Any] = None,
        notes: Optional[str] = None,
    ) -> str:
        """
        Create and persist a new experiment record.
        Optionally saves the trained model.
        """

        experiment_id = self._generate_experiment_id()
        exp_dir = self.base_path / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "experiment_id": experiment_id,
            "timestamp": datetime.utcnow().isoformat(),
            "dataset": {
                "name": dataset_name,
                "version": dataset_version,
            },
            "model": {
                "type": model_type,
                "hyperparameters": hyperparameters,
            },
            "preprocessing": preprocessing_config or {},
            "metrics": metrics,
            "random_seed": random_seed,
            "notes": notes,
        }

        self._save_json(exp_dir / "metadata.json", metadata)

        if model_object is not None:
            self._save_model(exp_dir / "model.pkl", model_object)

        return experiment_id

    def load_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """
        Load experiment metadata.
        """
        exp_dir = self.base_path / experiment_id
        metadata_path = exp_dir / "metadata.json"

        if not metadata_path.exists():
            raise FileNotFoundError(f"Experiment '{experiment_id}' not found.")

        return self._load_json(metadata_path)

    def load_model(self, experiment_id: str) -> Any:
        """
        Load saved model artifact.
        """
        model_path = self.base_path / experiment_id / "model.pkl"

        if not model_path.exists():
            raise FileNotFoundError(
                f"No saved model found for experiment '{experiment_id}'."
            )

        with open(model_path, "rb") as f:
            return pickle.load(f)

    def list_experiments(
        self,
        dataset_name: Optional[str] = None,
        model_type: Optional[str] = None,
        min_metric: Optional[Dict[str, float]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Filter experiments by:
        - dataset_name
        - model_type
        - minimum metric thresholds (e.g. {"accuracy": 0.9})
        - date range (ISO format strings)
        """

        from datetime import datetime

        experiments = {}

        for exp_dir in self.base_path.iterdir():
            if not exp_dir.is_dir():
                continue

            metadata_path = exp_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            metadata = self._load_json(metadata_path)

            # Dataset filter
            if dataset_name and metadata["dataset"]["name"] != dataset_name:
                continue

            # Model filter
            if model_type and metadata["model"]["type"] != model_type:
                continue

            # Metric threshold filter
            if min_metric:
                metrics = metadata.get("metrics", {})
                failed = False
                for key, threshold in min_metric.items():
                    if metrics.get(key, float("-inf")) < threshold:
                        failed = True
                        break
                if failed:
                    continue

            # Date range filter
            timestamp = datetime.fromisoformat(metadata["timestamp"])
            if date_from:
                if timestamp < datetime.fromisoformat(date_from):
                    continue
            if date_to:
                if timestamp > datetime.fromisoformat(date_to):
                    continue

            experiments[exp_dir.name] = {
                "timestamp": metadata.get("timestamp"),
                "dataset": metadata.get("dataset"),
                "model_type": metadata.get("model", {}).get("type"),
                "metrics": metadata.get("metrics"),
            }

        return experiments

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_experiment_id(self) -> str:
        return f"exp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    def _save_json(self, path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _load_json(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_model(self, path: Path, model: Any) -> None:
        with open(path, "wb") as f:
            pickle.dump(model, f)