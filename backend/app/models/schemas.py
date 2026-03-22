from pydantic import BaseModel
from typing import Optional


class PathwayInfo(BaseModel):
    name: str
    genes: list[str]
    gene_count: int


class ExpressionRequest(BaseModel):
    genes: list[str]
    pathway_name: str
    dataset_id: str = "gtex_v8"
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


class CoexpressionResult(BaseModel):
    # gene -> gene -> Pearson r
    correlation_matrix: dict[str, dict[str, float]]
    pathway_consistency_score: float
    top_correlated_pairs: list[dict]
    # gene -> {mean_tpm, median_tpm, cv, max_tissue, max_tpm}
    summary_stats: dict[str, dict]
    pca_variance_explained: list[float]
    # gene -> [PC1, PC2]
    pca_coordinates: dict[str, list[float]]


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
