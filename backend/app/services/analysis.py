"""
Co-expression analysis on GTEx expression matrices.
All functions are pure (no I/O) and operate on pandas DataFrames.
"""

import logging

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)


def build_dataframe(expression_matrix: dict[str, dict[str, float]]) -> pd.DataFrame:
    """
    Convert the raw {gene: {tissue: tpm}} dict to a DataFrame.
    Shape: genes × tissues. Missing values filled with 0.
    """
    df = pd.DataFrame(expression_matrix).T  # tissues as rows after transpose
    df = df.fillna(0.0)
    return df  # index=genes, columns=tissues


def compute_coexpression(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pearson correlation between genes across tissues on log2(TPM+1) values.
    Returns square DataFrame (genes × genes).
    """
    log_df = np.log2(df + 1)
    corr = log_df.T.corr(method="pearson")
    return corr.fillna(0.0)


def pathway_consistency_score(corr_matrix: pd.DataFrame) -> float:
    """
    Mean of all upper-triangle Pearson correlations.
    Score of 1 = perfectly co-expressed; 0 = no correlation; -1 = anti-correlated.
    """
    n = len(corr_matrix)
    if n < 2:
        return float("nan")
    upper = corr_matrix.values[np.triu_indices(n, k=1)]
    return float(np.mean(upper))


def top_correlated_pairs(corr_matrix: pd.DataFrame, n: int = 10) -> list[dict]:
    """Return top-n most positively correlated gene pairs."""
    pairs = []
    genes = list(corr_matrix.index)
    for i in range(len(genes)):
        for j in range(i + 1, len(genes)):
            pairs.append(
                {
                    "gene_a": genes[i],
                    "gene_b": genes[j],
                    "pearson_r": round(float(corr_matrix.iloc[i, j]), 4),
                }
            )
    pairs.sort(key=lambda x: x["pearson_r"], reverse=True)
    return pairs[:n]


def summary_stats(df: pd.DataFrame) -> dict[str, dict]:
    """
    Per-gene summary statistics across tissues.
    Returns {gene: {mean_tpm, median_tpm, std_tpm, cv, max_tissue, max_tpm}}.
    """
    result = {}
    for gene in df.index:
        row = df.loc[gene]
        mean_tpm = float(row.mean())
        std_tpm = float(row.std())
        result[gene] = {
            "mean_tpm": round(mean_tpm, 3),
            "median_tpm": round(float(row.median()), 3),
            "std_tpm": round(std_tpm, 3),
            "cv": round(std_tpm / (mean_tpm + 1e-6), 4),
            "max_tissue": str(row.idxmax()),
            "max_tpm": round(float(row.max()), 3),
        }
    return result


def run_pca(df: pd.DataFrame) -> tuple[list[float], dict[str, list[float]]]:
    """
    PCA on log2(TPM+1) expression matrix (genes as observations, tissues as features).
    Returns:
        variance_explained: list of explained variance ratios for up to 5 PCs
        coordinates: {gene: [PC1_score, PC2_score]}
    """
    log_df = np.log2(df + 1)
    n_components = min(5, len(df), len(df.columns))
    if n_components < 2:
        return [], {}

    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(log_df.values)

    variance_explained = [round(float(v), 4) for v in pca.explained_variance_ratio_]
    coordinates = {
        gene: [round(float(scores[i, 0]), 4), round(float(scores[i, 1]), 4)]
        for i, gene in enumerate(df.index)
    }
    logger.info(
        "PCA complete: %d components, top PC explains %.1f%% variance",
        n_components,
        variance_explained[0] * 100,
    )
    return variance_explained, coordinates


def run_full_analysis(expression_matrix: dict[str, dict[str, float]]) -> dict:
    """
    Entry point: run all analyses and return structured result ready for serialization.
    """
    logger.info(
        "Starting co-expression analysis: %d genes", len(expression_matrix)
    )
    df = build_dataframe(expression_matrix)

    corr_df = compute_coexpression(df)
    logger.info("Pairwise Pearson correlations computed (%dx%d matrix)", len(corr_df), len(corr_df))
    consistency = pathway_consistency_score(corr_df)
    logger.info("Pathway consistency score: %.4f", consistency)
    top_pairs = top_correlated_pairs(corr_df)
    stats_dict = summary_stats(df)
    var_explained, pca_coords = run_pca(df)

    return {
        "correlation_matrix": {
            gene: {g2: round(float(v), 4) for g2, v in row.items()}
            for gene, row in corr_df.to_dict().items()
        },
        "pathway_consistency_score": round(consistency, 4),
        "top_correlated_pairs": top_pairs,
        "summary_stats": stats_dict,
        "pca_variance_explained": var_explained,
        "pca_coordinates": pca_coords,
    }
