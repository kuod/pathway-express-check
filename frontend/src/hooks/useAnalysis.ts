import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { runAnalysis, downloadReport } from "@/api/client";
import type { AnalysisResponse, PathwayDetail, ReportRequest } from "@/types";
import type { LogLine } from "@/components/ActivityLog";

interface AnalysisState {
  selectedLibrary: string;
  selectedPathway: PathwayDetail | null;
  result: AnalysisResponse | null;
  datasetId: string;
}

function nowHHMMSS(): string {
  return new Date().toTimeString().slice(0, 8);
}

export function useAnalysis() {
  const [state, setState] = useState<AnalysisState>({
    selectedLibrary: "",
    selectedPathway: null,
    result: null,
    datasetId: "gtex_v8",
  });

  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const timerRefs = useRef<ReturnType<typeof setTimeout>[]>([]);

  function clearTimers() {
    timerRefs.current.forEach(clearTimeout);
    timerRefs.current = [];
  }

  function appendLog(line: LogLine) {
    setLogLines((prev) => [...prev, line]);
  }

  const mutation = useMutation({
    mutationFn: () => {
      if (!state.selectedPathway) throw new Error("No pathway selected");
      return runAnalysis(
        state.selectedPathway.genes,
        state.selectedPathway.name,
        state.datasetId
      );
    },
    onSuccess: (data) => {
      clearTimers();
      const found = data.expression.genes_found.length;
      const total = found + data.expression.genes_not_found.length;
      const tissues = data.expression.tissues.length;
      const score = data.coexpression.pathway_consistency_score;
      const varExplained = data.coexpression.pca_variance_explained;
      const topVar = varExplained.length > 0
        ? Math.round(varExplained[0] * 100)
        : null;

      setLogLines((prev) => {
        // replace any pending lines with real results
        const completed = prev.filter((l) => l.done);
        return [
          ...completed,
          { time: nowHHMMSS(), text: `Gene resolution: ${found}/${total} symbols matched` },
          { time: nowHHMMSS(), text: `Expression data: ${tissues} tissues, ${found} genes` },
          { time: nowHHMMSS(), text: "Pairwise Pearson correlations computed" },
          ...(topVar !== null
            ? [{ time: nowHHMMSS(), text: `PCA complete — ${varExplained.length} components, top variance ${topVar}%` }]
            : []),
          {
            time: nowHHMMSS(),
            text: `Analysis complete — consistency score ${score.toFixed(4)}`,
            done: true,
          },
        ];
      });

      setState((s) => ({ ...s, result: data }));
      toast.success(
        `Analysis complete — ${found} genes analyzed across ${tissues} tissues.`
      );
    },
    onError: (err: unknown) => {
      clearTimers();
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      appendLog({ time: nowHHMMSS(), text: `Error: ${detail ?? (err as Error).message}` });
      toast.error(`Analysis failed: ${detail ?? (err as Error).message}`);
    },
  });

  // Staged log messages while analysis is running
  useEffect(() => {
    if (!mutation.isPending) return;

    const geneCount = state.selectedPathway?.gene_count ?? 0;

    const schedule = (ms: number, text: string) => {
      const id = setTimeout(() => appendLog({ time: nowHHMMSS(), text }), ms);
      timerRefs.current.push(id);
    };

    schedule(0, `Resolving ${geneCount} gene symbols to versioned Ensembl IDs…`);
    schedule(800, "Querying GTEx reference API in parallel…");
    schedule(4000, "Fetching median expression data — GTEx batches 20 genes per request…");
    schedule(14000, "Still fetching… large gene sets can take 20–30 s");

    return clearTimers;
  }, [mutation.isPending]); // eslint-disable-line react-hooks/exhaustive-deps

  const downloadMutation = useMutation({
    mutationFn: (format: "html" | "docx" | "figures" | "csv") => {
      if (!state.result || !state.selectedPathway) throw new Error("No results to export");
      const req: ReportRequest = {
        pathway_name: state.selectedPathway.name,
        pathway_genes: state.selectedPathway.genes,
        expression: state.result.expression,
        coexpression: state.result.coexpression,
        dataset_info: state.datasetId === "gtex_v8" ? "GTEx v8" : state.datasetId,
        include_methods: true,
      };
      return downloadReport(format, req);
    },
    onSuccess: () => toast.success("Download started"),
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(`Export failed: ${detail ?? (err as Error).message}`);
    },
  });

  return {
    ...state,
    logLines,
    setLibrary: (lib: string) =>
      setState((s) => ({ ...s, selectedLibrary: lib, selectedPathway: null, result: null })),
    setPathway: (p: PathwayDetail | null) =>
      setState((s) => ({ ...s, selectedPathway: p, result: null })),
    setDatasetId: (id: string) => setState((s) => ({ ...s, datasetId: id })),
    runAnalysis: () => {
      setLogLines([]);
      clearTimers();
      mutation.mutate();
    },
    isAnalyzing: mutation.isPending,
    download: (fmt: "html" | "docx" | "figures" | "csv") => downloadMutation.mutate(fmt),
    isDownloading: downloadMutation.isPending,
  };
}
