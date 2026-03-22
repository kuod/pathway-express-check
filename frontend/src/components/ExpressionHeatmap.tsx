import Plot from "react-plotly.js";
import type { ExpressionResponse } from "@/types";

interface Props {
  expression: ExpressionResponse;
}

export function ExpressionHeatmap({ expression }: Props) {
  const { expression_matrix, tissues, genes_found } = expression;

  // Build z matrix: rows = genes, cols = tissues, log2(TPM+1)
  const z = genes_found.map((gene) =>
    tissues.map((t) => {
      const tpm = expression_matrix[gene]?.[t] ?? 0;
      return Math.log2(tpm + 1);
    })
  );

  return (
    <div className="card p-4">
      <h3 className="font-semibold text-gray-800 mb-3">Expression Across Tissues</h3>
      <Plot
        data={[
          {
            type: "heatmap",
            z,
            x: tissues,
            y: genes_found,
            colorscale: "Viridis",
            colorbar: { title: "log₂(TPM+1)", thickness: 15 },
            hoverongaps: false,
          },
        ]}
        layout={{
          margin: { l: 80, r: 20, t: 10, b: 120 },
          xaxis: { tickangle: -45, tickfont: { size: 9 } },
          yaxis: { tickfont: { size: 10 } },
          height: Math.max(300, genes_found.length * 22 + 160),
          autosize: true,
        }}
        config={{ responsive: true, displayModeBar: true, toImageButtonOptions: { format: "png", scale: 2 } }}
        style={{ width: "100%" }}
      />
    </div>
  );
}
