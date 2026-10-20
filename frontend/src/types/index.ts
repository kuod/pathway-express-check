export interface PathwaySearchResult {
  name: string;
  gene_count: number;
}

export interface PathwayDetail {
  name: string;
  library: string;
  genes: string[];
  gene_count: number;
}

export interface TissueInfo {
  tissue_site_detail_id: string;
  tissue_site_detail: string;
  tissue_site: string;
  color_hex?: string;
}

export interface ExpressionResponse {
  genes_found: string[];
  genes_not_found: string[];
  tissues: string[];
  // gene_symbol -> tissue_id -> median TPM
  expression_matrix: Record<string, Record<string, number>>;
}

export interface CoverageInfo {
  min_observations: number;
  min_observations_effective: number;
  gene_coverage: Record<string, { n_observed: number; n_tissues: number; low_coverage: boolean }>;
  tissue_coverage: Record<string, { n_observed: number; n_genes: number }>;
  genes_dropped_low_coverage: string[];
  tissues_with_missing: string[];
  pairs_total: number;
  pairs_evaluated: number;
  pca_genes: string[];
  pca_tissues_used: number;
  pca_tissues_dropped: string[];
}

export interface CoexpressionResult {
  // null = too few shared observed tissues (never imputed as 0)
  correlation_matrix: Record<string, Record<string, number | null>>;
  pathway_consistency_score: number;
  top_correlated_pairs: Array<{
    gene_a: string;
    gene_b: string;
    pearson_r: number;
  }>;
  summary_stats: Record<
    string,
    {
      mean_tpm: number | null;
      median_tpm: number | null;
      std_tpm: number | null;
      cv: number | null;
      max_tissue: string | null;
      max_tpm: number | null;
      n_observed?: number;
    }
  >;
  pca_variance_explained: number[];
  pca_coordinates: Record<string, [number, number]>;
  coverage?: CoverageInfo;
}

export interface AnalysisResponse {
  expression: ExpressionResponse;
  coexpression: CoexpressionResult;
}

export interface ReportRequest {
  pathway_name: string;
  pathway_genes: string[];
  expression: ExpressionResponse;
  coexpression: CoexpressionResult;
  dataset_info?: string;
  include_methods?: boolean;
}
