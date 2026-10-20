"""
Co-expression analysis on GTEx expression matrices.
All functions are pure (no I/O) and operate on pandas DataFrames.
"""

import logging

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.decomposition import PCA

from app.config import settings

logger = logging.getLogger(__name__)


def build_dataframe(expression_matrix: dict[str, dict[str, float]]) -> pd.DataFrame:
    """
    Convert the raw {gene: {tissue: tpm}} dict to a DataFrame.
    Shape: genes x tissues. Missing values stay NaN: they are never imputed
    (a missing measurement is not a measured zero).
    """
    df = pd.DataFrame(expression_matrix).T  # tissues as rows after transpose
    return df.astype(float)  # index=genes, columns=tissues


def effective_min_obs(n_tissues: int, min_obs: int | None = None) -> int:
    """
    Minimum shared observations required for a correlation.

    Defaults to ``settings.min_observations``. It is capped at the number of
    tissues in the matrix (and floored at 2, the least for which Pearson r is
    defined), so a deliberately tiny tissue selection is still analysable;
    that case is not hidden, it is reported via ``min_observations_effective``.
    """
    m = settings.min_observations if min_obs is None else min_obs
    return max(2, min(m, n_tissues)) if n_tissues >= 2 else 2


def compute_coexpression(df: pd.DataFrame, min_obs: int | None = None) -> pd.DataFrame:
    """
    Pairwise-complete Pearson correlation between genes across tissues on
    log2(TPM+1) values. Each pair uses only tissues where both genes were
    observed. Pairs with fewer than the minimum shared observations are NaN
    (not 0). A pair where either gene is constant over the shared tissues has
    undefined r and is reported as 0.0 (no detectable co-variation), as before.
    Returns square DataFrame (genes x genes).
    """
    m = effective_min_obs(df.shape[1], min_obs)
    x = np.log2(df.astype(float) + 1).values
    n = x.shape[0]
    out = np.full((n, n), np.nan)
    ok = ~np.isnan(x)
    for i in range(n):
        for j in range(i, n):
            both = ok[i] & ok[j]
            if both.sum() < m:
                continue
            a, b = x[i, both], x[j, both]
            da, db = a - a.mean(), b - b.mean()
            denom = np.sqrt((da @ da) * (db @ db))
            r = 0.0 if denom < 1e-12 else float(np.clip((da @ db) / denom, -1.0, 1.0))
            out[i, j] = out[j, i] = r
    return pd.DataFrame(out, index=df.index, columns=df.index)


def coverage_info(df: pd.DataFrame, min_obs: int | None = None) -> dict:
    """Observed counts per gene / tissue, plus which genes could not be correlated."""
    m = effective_min_obs(df.shape[1], min_obs)
    gene_obs = df.notna().sum(axis=1)
    tissue_obs = df.notna().sum(axis=0)
    n_t, n_g = df.shape[1], df.shape[0]
    return {
        "min_observations": settings.min_observations if min_obs is None else min_obs,
        "min_observations_effective": m,
        "gene_coverage": {
            g: {"n_observed": int(gene_obs[g]), "n_tissues": n_t,
                "low_coverage": bool(gene_obs[g] < m)}
            for g in df.index
        },
        "tissue_coverage": {
            t: {"n_observed": int(tissue_obs[t]), "n_genes": n_g}
            for t in df.columns
        },
        "genes_dropped_low_coverage": [g for g in df.index if gene_obs[g] < m],
        "tissues_with_missing": [t for t in df.columns if tissue_obs[t] < n_g],
    }


def pathway_consistency_score(corr_matrix: pd.DataFrame) -> float:
    """
    Mean of all upper-triangle Pearson correlations.
    Score of 1 = perfectly co-expressed; 0 = no correlation; -1 = anti-correlated.
    """
    n = len(corr_matrix)
    if n < 2:
        return float("nan")
    upper = corr_matrix.values[np.triu_indices(n, k=1)]
    upper = upper[~np.isnan(upper)]  # pairs without enough data are excluded, not counted as 0
    if upper.size == 0:
        return float("nan")
    return float(np.mean(upper))


def top_correlated_pairs(corr_matrix: pd.DataFrame, n: int = 10) -> list[dict]:
    """Return top-n most positively correlated gene pairs."""
    pairs = []
    genes = list(corr_matrix.index)
    for i in range(len(genes)):
        for j in range(i + 1, len(genes)):
            if np.isnan(corr_matrix.iloc[i, j]):
                continue
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
    Statistics use observed tissues only. Returns
    {gene: {mean_tpm, median_tpm, std_tpm, cv, max_tissue, max_tpm, n_observed}}.
    """
    result = {}
    for gene in df.index:
        row = df.loc[gene].dropna()
        if row.empty:  # no observations at all
            result[gene] = {"mean_tpm": None, "median_tpm": None, "std_tpm": None,
                            "cv": None, "max_tissue": None, "max_tpm": None, "n_observed": 0}
            continue
        mean_tpm = float(row.mean())
        std_tpm = float(row.std())
        if np.isnan(std_tpm):  # single tissue: sample std undefined
            std_tpm = 0.0
        result[gene] = {
            "mean_tpm": round(mean_tpm, 3),
            "median_tpm": round(float(row.median()), 3),
            "std_tpm": round(std_tpm, 3),
            "cv": round(std_tpm / (mean_tpm + 1e-6), 4),
            "max_tissue": str(row.idxmax()),
            "max_tpm": round(float(row.max()), 3),
            "n_observed": int(len(row)),
        }
    return result


def pca_input(df: pd.DataFrame, min_obs: int | None = None) -> pd.DataFrame:
    """
    PCA needs a complete matrix and must not see imputed values. Keep genes with
    enough observations, then only tissues observed for all of those genes.
    """
    m = effective_min_obs(df.shape[1], min_obs)
    sub = df.loc[df.notna().sum(axis=1) >= m]
    return sub.loc[:, sub.notna().all(axis=0)]


def run_pca(df: pd.DataFrame, min_obs: int | None = None) -> tuple[list[float], dict[str, list[float]]]:
    """
    PCA on log2(TPM+1) expression matrix (genes as observations, tissues as features),
    restricted to the complete sub-matrix given by `pca_input`.
    Returns:
        variance_explained: list of explained variance ratios for up to 5 PCs
        coordinates: {gene: [PC1_score, PC2_score]}
    """
    df = pca_input(df, min_obs)
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
    logger.info("Pairwise-complete Pearson correlations computed (%dx%d matrix)", len(corr_df), len(corr_df))
    consistency = pathway_consistency_score(corr_df)
    logger.info("Pathway consistency score: %.4f", consistency)
    top_pairs = top_correlated_pairs(corr_df)
    stats_dict = summary_stats(df)
    var_explained, pca_coords = run_pca(df)
    cov = coverage_info(df)

    n = len(corr_df)
    upper = corr_df.values[np.triu_indices(n, k=1)]
    pca_df = pca_input(df)
    cov.update(
        pairs_total=int(upper.size),
        pairs_evaluated=int((~np.isnan(upper)).sum()),
        pca_genes=list(pca_df.index),
        pca_tissues_used=len(pca_df.columns),
        pca_tissues_dropped=[t for t in df.columns if t not in pca_df.columns],
    )

    return {
        "correlation_matrix": {
            gene: {g2: (None if np.isnan(v) else round(float(v), 4)) for g2, v in row.items()}
            for gene, row in corr_df.to_dict().items()
        },
        # NaN only for <2 genes (legacy contract); None when >=2 genes but no pair
        # has enough shared tissues. Callers must treat both as "no score".
        "pathway_consistency_score": (
            None if np.isnan(consistency) and n >= 2 else round(consistency, 4)
        ),
        "top_correlated_pairs": top_pairs,
        "summary_stats": stats_dict,
        "pca_variance_explained": var_explained,
        "pca_coordinates": pca_coords,
        "coverage": cov,
    }
