import type { AnalysisResponse, PathwayDetail, ReportRequest } from "@/types";
import { downloadReport } from "@/api/client";
import toast from "react-hot-toast";
import { useState } from "react";

interface Props {
  pathway: PathwayDetail;
  result: AnalysisResponse;
  datasetInfo?: string;
}

const EXPORTS = [
  { fmt: "html" as const, label: "HTML Preprint", desc: "Printable academic report with embedded figures" },
  { fmt: "docx" as const, label: "Word Document", desc: "Editable .docx preprint template" },
  { fmt: "figures" as const, label: "Figures (ZIP)", desc: "High-res PNG figures (300 dpi)" },
  { fmt: "csv" as const, label: "Data (Excel)", desc: "Expression matrix, correlations, and stats" },
];

export function ExportPanel({ pathway, result, datasetInfo = "GTEx v8" }: Props) {
  const [loading, setLoading] = useState<string | null>(null);

  async function handleDownload(fmt: typeof EXPORTS[number]["fmt"]) {
    const req: ReportRequest = {
      pathway_name: pathway.name,
      pathway_genes: pathway.genes,
      expression: result.expression,
      coexpression: result.coexpression,
      dataset_info: datasetInfo,
      include_methods: true,
    };
    setLoading(fmt);
    try {
      await downloadReport(fmt, req);
      toast.success("Download started");
    } catch {
      toast.error("Export failed");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="card p-4">
      <h3 className="font-semibold text-gray-800 mb-3">Export Results</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {EXPORTS.map(({ fmt, label, desc }) => (
          <button
            key={fmt}
            className="btn-secondary text-left px-3 py-2.5"
            disabled={loading !== null}
            onClick={() => handleDownload(fmt)}
          >
            <div className="font-medium text-sm">
              {loading === fmt ? "Generating…" : label}
            </div>
            <div className="text-xs text-gray-400 mt-0.5">{desc}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
