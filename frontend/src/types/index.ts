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

export interface CoexpressionResult {
  correlation_matrix: Record<string, Record<string, number>>;
  pathway_consistency_score: number;
  top_correlated_pairs: Array<{
    gene_a: string;
    gene_b: string;
    pearson_r: number;
  }>;
  summary_stats: Record<
    string,
    {
      mean_tpm: number;
      median_tpm: number;
      std_tpm: number;
      cv: number;
      max_tissue: string;
      max_tpm: number;
    }
  >;
  pca_variance_explained: number[];
  pca_coordinates: Record<string, [number, number]>;
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
