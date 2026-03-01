# core/synthesis.py

from typing import Dict, Tuple, Optional
import pandas as pd

from sdv.single_table import GaussianCopulaSynthesizer
from sdv.metadata import SingleTableMetadata


def build_metadata(df: pd.DataFrame) -> SingleTableMetadata:
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(df)
    return metadata


def train_synthesizer(
    df: pd.DataFrame
) -> Tuple[GaussianCopulaSynthesizer, Dict]:

    metadata = build_metadata(df)

    synthesizer = GaussianCopulaSynthesizer(
        metadata=metadata,
    )

    synthesizer.fit(df)

    config = {
        "operation": "train_synthesizer",
        "model": "GaussianCopula",
        "columns": list(df.columns),
    }

    return synthesizer, config


def generate_synthetic_data(
    synthesizer: GaussianCopulaSynthesizer,
    num_rows: int,
) -> Tuple[pd.DataFrame, Dict]:

    synthetic_df = synthesizer.sample(num_rows)

    config = {
        "operation": "generate_synthetic_data",
        "num_rows": num_rows,
    }

    return synthetic_df, config


def synthesize(
    df: pd.DataFrame,
    num_rows: int
) -> Tuple[pd.DataFrame, Dict]:

    synthesizer, train_config = train_synthesizer(
        df=df
    )

    synthetic_df, gen_config = generate_synthetic_data(
        synthesizer=synthesizer,
        num_rows=num_rows,
    )

    config = {
        "operation": "synthesis_pipeline",
        "train": train_config,
        "generate": gen_config,
    }

    return synthetic_df, config