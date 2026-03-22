import axios from "axios";
import type {
  AnalysisResponse,
  PathwayDetail,
  PathwaySearchResult,
  ReportRequest,
  TissueInfo,
} from "@/types";

const api = axios.create({ baseURL: "/api", timeout: 120_000 });

// Pathways
export const fetchLibraries = (): Promise<string[]> =>
  api.get<string[]>("/pathways/libraries").then((r) => r.data);

export const searchPathways = (
  library: string,
  query = "",
  maxResults = 50
): Promise<PathwaySearchResult[]> =>
  api
    .get<PathwaySearchResult[]>("/pathways/search", {
      params: { library, query, max_results: maxResults },
    })
    .then((r) => r.data);

export const fetchPathway = (
  library: string,
  name: string
): Promise<PathwayDetail> =>
  api
    .get<PathwayDetail>(`/pathways/${encodeURIComponent(library)}/${encodeURIComponent(name)}`)
    .then((r) => r.data);

// Expression / Analysis
export const fetchTissues = (datasetId = "gtex_v8"): Promise<TissueInfo[]> =>
  api
    .get<TissueInfo[]>("/expression/tissues", { params: { dataset_id: datasetId } })
    .then((r) => r.data);

export const runAnalysis = (
  genes: string[],
  pathwayName: string,
  datasetId = "gtex_v8",
  tissueIds?: string[]
): Promise<AnalysisResponse> =>
  api
    .post<AnalysisResponse>("/expression/analyze", {
      genes,
      pathway_name: pathwayName,
      dataset_id: datasetId,
      tissue_ids: tissueIds ?? null,
    })
    .then((r) => r.data);

// Reports
export const downloadReport = async (
  format: "html" | "docx" | "figures" | "csv",
  req: ReportRequest
): Promise<void> => {
  const urlMap: Record<string, string> = {
    html: "/reports/html",
    docx: "/reports/docx",
    figures: "/reports/figures/zip",
    csv: "/reports/data/csv",
  };
  const mimeMap: Record<string, string> = {
    html: "text/html",
    docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    figures: "application/zip",
    csv: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  };
  const extMap: Record<string, string> = {
    html: "html",
    docx: "docx",
    figures: "zip",
    csv: "xlsx",
  };

  const res = await api.post(urlMap[format], req, { responseType: "blob" });
  const blob = new Blob([res.data], { type: mimeMap[format] });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${req.pathway_name.replace(/\s+/g, "_")}_report.${extMap[format]}`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 100);
};
