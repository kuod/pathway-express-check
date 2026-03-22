import { useAnalysis } from "@/hooks/useAnalysis";
import { PathwaySearch } from "@/components/PathwaySearch";
import { GeneList } from "@/components/GeneList";
import { ExpressionHeatmap } from "@/components/ExpressionHeatmap";
import { CorrelationHeatmap } from "@/components/CorrelationHeatmap";
import { SummaryStats } from "@/components/SummaryStats";
import { ExportPanel } from "@/components/ExportPanel";
import { ActivityLog } from "@/components/ActivityLog";

const DATASET_OPTIONS = [
  { id: "gtex_v8", label: "GTEx v8" },
  { id: "gtex_v10", label: "GTEx v10" },
];

export function Dashboard() {
  const {
    selectedLibrary,
    selectedPathway,
    result,
    datasetId,
    logLines,
    setLibrary,
    setPathway,
    setDatasetId,
    runAnalysis,
    isAnalyzing,
  } = useAnalysis();

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Pathway Express Check</h1>
            <p className="text-xs text-gray-500 mt-0.5">
              MSigDB pathway co-expression in GTEx tissues
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-xs text-gray-500">Dataset:</label>
            <select
              className="select w-36"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
            >
              {DATASET_OPTIONS.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        {/* Left sidebar */}
        <div className="space-y-4">
          <PathwaySearch
            selectedLibrary={selectedLibrary}
            onLibraryChange={setLibrary}
            onPathwaySelect={setPathway}
          />

          {selectedPathway && (
            <>
              <GeneList
                pathway={selectedPathway}
                genesNotFound={result?.expression.genes_not_found}
              />

              <button
                className="btn-primary w-full"
                disabled={isAnalyzing}
                onClick={runAnalysis}
              >
                {isAnalyzing ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>
                    Fetching expression data…
                  </span>
                ) : (
                  "Run Analysis"
                )}
              </button>

              {result && (
                <ExportPanel
                  pathway={selectedPathway}
                  result={result}
                  datasetInfo={DATASET_OPTIONS.find((o) => o.id === datasetId)?.label}
                />
              )}
            </>
          )}
        </div>

        {/* Main content */}
        <div className="space-y-6">
          {!selectedPathway && (
            <div className="card p-12 text-center text-gray-400">
              <p className="text-lg">Select a library and pathway to begin.</p>
              <p className="text-sm mt-1">
                Gene sets from MSigDB will be cross-referenced against GTEx expression data.
              </p>
            </div>
          )}

          {selectedPathway && !result && !isAnalyzing && (
            <div className="card p-12 text-center text-gray-400">
              <p>Click <strong>Run Analysis</strong> to fetch expression data and compute co-expression.</p>
            </div>
          )}

          {(isAnalyzing || logLines.length > 0) && !result && (
            <ActivityLog lines={logLines} />
          )}

          {result && (
            <>
              <ExpressionHeatmap expression={result.expression} />
              <CorrelationHeatmap coexpression={result.coexpression} />
              <SummaryStats coexpression={result.coexpression} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
