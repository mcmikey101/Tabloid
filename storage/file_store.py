# storage/file_store.py

from pathlib import Path
from typing import List
import pandas as pd
import shutil


class FileStore:
    """
    Handles low-level filesystem operations for datasets and versions.

    Storage layout:

    data/
        dataset_name/
            versions/
                version_name.pkl
            metadata.json
    """

    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Dataset Directory Management
    # ------------------------------------------------------------------

    def create_dataset_directory(self, dataset_name: str) -> None:
        dataset_path = self.get_dataset_path(dataset_name)
        versions_path = dataset_path / "versions"

        versions_path.mkdir(parents=True, exist_ok=True)

    def delete_dataset(self, dataset_name: str) -> None:
        dataset_path = self.get_dataset_path(dataset_name)
        if dataset_path.exists():
            shutil.rmtree(dataset_path)

    def list_datasets(self) -> List[str]:
        return [
            d.name
            for d in self.base_path.iterdir()
            if d.is_dir()
        ]
    
    def get_dataset_path(self, dataset_name: str) -> Path:
        return self.base_path / dataset_name
    
    def get_versions_path(self, dataset_name: str) -> Path:
        return self.get_dataset_path(dataset_name) / "versions"
    

    # ------------------------------------------------------------------
    # Version Storage (Pickle)
    # ------------------------------------------------------------------

    def save_version(
        self,
        dataset_name: str,
        version_name: str,
        df: pd.DataFrame,
    ) -> None:
        version_path = self._version_file_path(dataset_name, version_name)
        df.to_pickle(version_path)

    def load_version(
        self,
        dataset_name: str,
        version_name: str,
    ) -> pd.DataFrame:
        version_path = self._version_file_path(dataset_name, version_name)

        if not version_path.exists():
            raise FileNotFoundError(
                f"Version '{version_name}' not found for dataset '{dataset_name}'."
            )

        return pd.read_pickle(version_path)

    def delete_version(
        self,
        dataset_name: str,
        version_name: str,
    ) -> None:
        version_path = self._version_file_path(dataset_name, version_name)
        if version_path.exists():
            version_path.unlink()

    def list_versions(self, dataset_name: str) -> List[str]:
        versions_path = self._dataset_path(dataset_name) / "versions"

        if not versions_path.exists():
            return []

        return [
            f.stem
            for f in versions_path.glob("*.pkl")
        ]

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _version_file_path(
        self,
        dataset_name: str,
        version_name: str,
    ) -> Path:
        return (
            self.get_dataset_path(dataset_name)
            / "versions"
            / f"{version_name}.pkl"
        )