import type { CoexpressionResult } from "@/types";

interface Props {
  coexpression: CoexpressionResult;
}

export function SummaryStats({ coexpression }: Props) {
  const { summary_stats, top_correlated_pairs } = coexpression;
  const genes = Object.keys(summary_stats).sort();

  return (
    <div className="space-y-4">
      {/* Per-gene stats table */}
      <div className="card p-4">
        <h3 className="font-semibold text-gray-800 mb-3">Per-gene Expression Statistics</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200">
                {["Gene", "Mean TPM", "Median TPM", "Std", "CV", "Max Tissue", "Max TPM"].map((h) => (
                  <th key={h} className="text-left py-1.5 px-2 text-gray-500 font-medium whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {genes.map((gene, i) => {
                const s = summary_stats[gene];
                return (
                  <tr key={gene} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                    <td className="py-1.5 px-2 font-mono font-medium">{gene}</td>
                    <td className="py-1.5 px-2">{s.mean_tpm.toFixed(2)}</td>
                    <td className="py-1.5 px-2">{s.median_tpm.toFixed(2)}</td>
                    <td className="py-1.5 px-2">{s.std_tpm.toFixed(2)}</td>
                    <td className="py-1.5 px-2">{s.cv.toFixed(3)}</td>
                    <td className="py-1.5 px-2 max-w-[160px] truncate" title={s.max_tissue}>
                      {s.max_tissue}
                    </td>
                    <td className="py-1.5 px-2">{s.max_tpm.toFixed(1)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top correlated pairs */}
      <div className="card p-4">
        <h3 className="font-semibold text-gray-800 mb-3">Top Co-expressed Gene Pairs</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200">
                {["Rank", "Gene A", "Gene B", "Pearson r"].map((h) => (
                  <th key={h} className="text-left py-1.5 px-2 text-gray-500 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {top_correlated_pairs.map((pair, i) => (
                <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="py-1.5 px-2 text-gray-400">{i + 1}</td>
                  <td className="py-1.5 px-2 font-mono">{pair.gene_a}</td>
                  <td className="py-1.5 px-2 font-mono">{pair.gene_b}</td>
                  <td className="py-1.5 px-2">
                    <span
                      className={`font-medium ${
                        pair.pearson_r > 0.7
                          ? "text-green-700"
                          : pair.pearson_r > 0.4
                          ? "text-blue-700"
                          : "text-gray-700"
                      }`}
                    >
                      {pair.pearson_r.toFixed(4)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
