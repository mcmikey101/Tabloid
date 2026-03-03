# core/synthesis.py

from typing import Dict, Tuple, Optional, Any

import pandas as pd

from sdv.metadata import SingleTableMetadata
from sdv.single_table import (
    GaussianCopulaSynthesizer,
    CTGANSynthesizer,
    TVAESynthesizer,
)

from sdv.evaluation.single_table import evaluate_quality


# ----------------------------------------------------------------------
# Metadata
# ----------------------------------------------------------------------

def build_metadata(df: pd.DataFrame) -> SingleTableMetadata:
    metadata = SingleTableMetadata()
    metadata.detect_from_dataframe(df)
    return metadata


# ----------------------------------------------------------------------
# Model Factory
# ----------------------------------------------------------------------

def _create_synthesizer(
    model_type: str,
    metadata: SingleTableMetadata,
    **model_kwargs: Any,
):
    model_type = model_type.lower()

    if model_type == "gaussian_copula":
        return GaussianCopulaSynthesizer(
            metadata=metadata,
            **model_kwargs,
        )

    if model_type == "ctgan":
        return CTGANSynthesizer(
            metadata=metadata,
            **model_kwargs,
        )

    if model_type == "tvae":
        return TVAESynthesizer(
            metadata=metadata,
            **model_kwargs,
        )

    raise ValueError(
        "Unsupported model_type. Choose from: "
        "gaussian_copula, ctgan, tvae."
    )


# ----------------------------------------------------------------------
# Training
# ----------------------------------------------------------------------

def train_synthesizer(
    df: pd.DataFrame,
    model_type: str = "gaussian_copula",
    **model_kwargs: Any,
) -> Tuple[Any, Dict]:

    metadata = build_metadata(df)

    synthesizer = _create_synthesizer(
        model_type=model_type,
        metadata=metadata,
        **model_kwargs,
    )

    synthesizer.fit(df)

    config = {
        "operation": "train_synthesizer",
        "model": model_type,
        "model_params": model_kwargs,
        "columns": list(df.columns),
    }

    return synthesizer, config


# ----------------------------------------------------------------------
# Sampling
# ----------------------------------------------------------------------

def generate_synthetic_data(
    synthesizer,
    num_rows: int,
) -> Tuple[pd.DataFrame, Dict]:

    synthetic_df = synthesizer.sample(num_rows)

    config = {
        "operation": "generate_synthetic_data",
        "num_rows": num_rows,
    }

    return synthetic_df, config


# ----------------------------------------------------------------------
# Quality Evaluation
# ----------------------------------------------------------------------

def evaluate_synthetic_quality(
    real_df: pd.DataFrame,
    synthetic_df: pd.DataFrame,
) -> Dict:

    metadata = build_metadata(real_df)

    report = evaluate_quality(
        real_data=real_df,
        synthetic_data=synthetic_df,
        metadata=metadata,
    )

    properties = report.get_properties()

    details = {}
    for prop in properties["Property"]:
        details[prop] = report.get_details(prop)
        details[prop] = details[prop].replace({float("nan"): None}).to_dict()

    results = {
        "overall_score": report.get_score(),
        "properties": properties.to_dict(),
        "details": details,
    }

    return results


# ----------------------------------------------------------------------
# Full Pipeline
# ----------------------------------------------------------------------

def synthesize(
    df: pd.DataFrame,
    num_rows: int,
    model_type: str = "gaussian_copula",
    evaluate: bool = True,
    **model_kwargs: Any,
) -> Tuple[pd.DataFrame, Dict]:

    synthesizer, train_config = train_synthesizer(
        df=df,
        model_type=model_type,
        **model_kwargs,
    )

    synthetic_df, gen_config = generate_synthetic_data(
        synthesizer=synthesizer,
        num_rows=num_rows,
    )

    quality_results = None
    if evaluate:
        quality_results = evaluate_synthetic_quality(
            real_df=df,
            synthetic_df=synthetic_df,
        )

    config = {
        "operation": "synthesis_pipeline",
        "train": train_config,
        "generate": gen_config,
        "quality_evaluation": quality_results,
    }

    return synthetic_df, config