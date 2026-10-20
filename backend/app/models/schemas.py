from pydantic import BaseModel
from typing import Optional

from app.config import settings


class PathwayInfo(BaseModel):
    name: str
    genes: list[str]
    gene_count: int


class ExpressionRequest(BaseModel):
    genes: list[str]
    pathway_name: str
    dataset_id: str = settings.gtex_dataset_id
    tissue_ids: Optional[list[str]] = None  # None = all tissues


class TissueInfo(BaseModel):
    tissue_site_detail_id: str
    tissue_site_detail: str
    tissue_site: str
    color_hex: Optional[str] = None


class ExpressionResponse(BaseModel):
    genes_found: list[str]
    genes_not_found: list[str]
    tissues: list[str]
    # gene_symbol -> tissue_site_detail_id -> median TPM
    expression_matrix: dict[str, dict[str, float]]


class GeneCoverage(BaseModel):
    n_observed: int  # tissues with a measured value
    n_tissues: int
    low_coverage: bool  # n_observed below the minimum: excluded from correlations


class TissueCoverage(BaseModel):
    n_observed: int  # genes with a measured value
    n_genes: int


class CoverageInfo(BaseModel):
    """Missing-data accounting. Missing values are never imputed as zero."""
    min_observations: int  # configured minimum shared tissues per gene pair
    min_observations_effective: int  # after capping at the number of tissues
    gene_coverage: dict[str, GeneCoverage]
    tissue_coverage: dict[str, TissueCoverage]
    genes_dropped_low_coverage: list[str]
    tissues_with_missing: list[str]
    pairs_total: int
    pairs_evaluated: int  # pairs with enough shared tissues (used in the score)
    pca_genes: list[str]
    pca_tissues_used: int  # PCA uses only tissues observed for all PCA genes
    pca_tissues_dropped: list[str]


class CoexpressionResult(BaseModel):
    # gene -> gene -> Pearson r (pairwise-complete); null = too few shared tissues
    correlation_matrix: dict[str, dict[str, Optional[float]]]
    pathway_consistency_score: float
    top_correlated_pairs: list[dict]
    # gene -> {mean_tpm, median_tpm, cv, max_tissue, max_tpm}
    summary_stats: dict[str, dict]
    pca_variance_explained: list[float]
    # gene -> [PC1, PC2]
    pca_coordinates: dict[str, list[float]]
    coverage: Optional[CoverageInfo] = None  # absent in older payloads


class AnalysisResponse(BaseModel):
    expression: ExpressionResponse
    coexpression: CoexpressionResult


class ReportRequest(BaseModel):
    pathway_name: str
    pathway_genes: list[str]
    expression: ExpressionResponse
    coexpression: CoexpressionResult
    dataset_info: str = "GTEx v8"
    include_methods: bool = True
