# core/dataset_manager.py

from pathlib import Path
from typing import List, Optional

import pandas as pd

from storage.file_store import FileStore
from core.version_manager import VersionManager


class DatasetManager:
    """
    High-level dataset orchestration.

    Responsibilities:
    - Create dataset from file
    - Initialize raw version
    - Load dataset versions
    - Delete dataset
    - List datasets
    """

    def __init__(
        self,
        file_store: FileStore,
        version_manager: VersionManager,
    ):
        self.file_store = file_store
        self.version_manager = version_manager

    # ------------------------------------------------------------------
    # Dataset Creation
    # ------------------------------------------------------------------

    def create_dataset(
        self,
        dataset_name: str,
        file_path: str,
    ) -> None:
        """
        Create dataset from CSV or Excel file.
        Initializes 'raw' version.
        """

        # Create directory
        self.file_store.create_dataset_directory(dataset_name)

        # Load file
        df = self._load_input_file(file_path)

        # Save raw version
        self.version_manager.create_version(
            dataset_name=dataset_name,
            version_name="raw",
            df=df,
            parent_version=None,
            operation="import",
            config={"source_file": str(file_path)}
        )

    # ------------------------------------------------------------------
    # Dataset Access
    # ------------------------------------------------------------------

    def load_version(
        self,
        dataset_name: str,
        version_name: str,
    ) -> pd.DataFrame:
        return self.file_store.load_version(dataset_name, version_name)

    def list_datasets(self) -> List[str]:
        return self.file_store.list_datasets()

    def list_versions(self, dataset_name: str) -> List[str]:
        return self.version_manager.list_versions(dataset_name)

    # ------------------------------------------------------------------
    # Dataset Deletion
    # ------------------------------------------------------------------

    def delete_dataset(
        self,
        dataset_name: str,
    ) -> None:
        self.file_store.delete_dataset(dataset_name)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _load_input_file(self, file_path: str) -> pd.DataFrame:
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File '{file_path}' not found.")

        if path.suffix.lower() == ".csv":
            return pd.read_csv(path)

        if path.suffix.lower() in [".xlsx", ".xls"]:
            return pd.read_excel(path)

        raise ValueError(
            "Unsupported file format. Only CSV and Excel are allowed."
        )