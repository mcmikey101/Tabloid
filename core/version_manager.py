# core/version_manager.py

from datetime import datetime
from typing import Dict, Optional, List

import pandas as pd

from storage.file_store import FileStore


class VersionManager:
    """
    Handles dataset version creation and lineage tracking.
    Supports branching through parent references.
    """

    META_FILENAME = "versions_meta.json"

    def __init__(self, file_store: FileStore):
        self.file_store = file_store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_version(
        self,
        dataset_name: str,
        version_name: str,
        df: pd.DataFrame,
        parent_version: Optional[str],
        operation: str,
        config: Optional[Dict] = None
    ) -> None:
        """
        Create a new dataset version and register metadata.
        """

        # Save dataframe
        self.file_store.save_version(dataset_name, version_name, df)

        # Load existing metadata
        meta = self._load_versions_meta(dataset_name)

        if version_name in meta:
            raise ValueError(f"Version '{version_name}' already exists.")

        if parent_version is not None and parent_version not in meta:
            raise ValueError(
                f"Parent version '{parent_version}' does not exist."
            )

        meta[version_name] = {
            "parent": parent_version,
            "operation": operation,
            "config": config or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        self._save_versions_meta(dataset_name, meta)

    def get_version_metadata(
        self,
        dataset_name: str,
        version_name: str,
    ) -> Dict:
        meta = self._load_versions_meta(dataset_name)
        if version_name not in meta:
            raise ValueError(f"Version '{version_name}' not found.")
        return meta[version_name]

    def list_versions(self, dataset_name: str) -> List[str]:
        meta = self._load_versions_meta(dataset_name)
        return list(meta.keys())

    def get_lineage(
        self,
        dataset_name: str,
        version_name: str,
    ) -> List[str]:
        """
        Returns lineage from root to the given version.
        """
        meta = self._load_versions_meta(dataset_name)

        if version_name not in meta:
            raise ValueError(f"Version '{version_name}' not found.")

        lineage = []
        current = version_name

        while current is not None:
            lineage.append(current)
            current = meta[current]["parent"]

        lineage.reverse()
        return lineage

    def delete_version(
        self,
        dataset_name: str,
        version_name: str,
    ) -> None:
        """
        Deletes a version only if it has no children.
        """
        meta = self._load_versions_meta(dataset_name)

        if version_name not in meta:
            raise ValueError(f"Version '{version_name}' not found.")

        # Check for children
        for v, info in meta.items():
            if info["parent"] == version_name:
                raise ValueError(
                    f"Cannot delete version '{version_name}' "
                    f"because it has child version '{v}'."
                )

        # Remove file
        versions_path = self.file_store.get_versions_path(dataset_name)
        version_file = versions_path / f"{version_name}.pkl"
        if version_file.exists():
            version_file.unlink()

        # Remove metadata
        del meta[version_name]
        self._save_versions_meta(dataset_name, meta)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_versions_meta(self, dataset_name: str) -> Dict:
        dataset_path = self.file_store.get_dataset_path(dataset_name)
        meta_path = dataset_path / self.META_FILENAME

        if not meta_path.exists():
            return {}

        import json
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_versions_meta(
        self,
        dataset_name: str,
        meta: Dict,
    ) -> None:
        dataset_path = self.file_store.get_dataset_path(dataset_name)
        meta_path = dataset_path / self.META_FILENAME

        import json
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4)