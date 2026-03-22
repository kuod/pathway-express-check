import Plot from "react-plotly.js";
import type { CoexpressionResult } from "@/types";

interface Props {
  coexpression: CoexpressionResult;
}

export function CorrelationHeatmap({ coexpression }: Props) {
  const { correlation_matrix, pca_coordinates, pca_variance_explained } = coexpression;
  const genes = Object.keys(correlation_matrix);

  const z = genes.map((g1) => genes.map((g2) => correlation_matrix[g1]?.[g2] ?? 0));

  // PCA scatter data
  const pcaX = genes.map((g) => pca_coordinates[g]?.[0] ?? 0);
  const pcaY = genes.map((g) => pca_coordinates[g]?.[1] ?? 0);

  return (
    <div className="space-y-4">
      {/* Correlation heatmap */}
      <div className="card p-4">
        <h3 className="font-semibold text-gray-800 mb-1">Co-expression Correlation Matrix</h3>
        <p className="text-xs text-gray-500 mb-3">
          Pathway consistency score:{" "}
          <span className="font-semibold text-blue-700">
            {coexpression.pathway_consistency_score.toFixed(3)}
          </span>{" "}
          (mean pairwise Pearson r; range −1 to +1)
        </p>
        <Plot
          data={[
            {
              type: "heatmap",
              z,
              x: genes,
              y: genes,
              colorscale: "RdBu",
              reversescale: true,
              zmin: -1,
              zmax: 1,
              colorbar: { title: "Pearson r", thickness: 15 },
            },
          ]}
          layout={{
            margin: { l: 80, r: 20, t: 10, b: 80 },
            xaxis: { tickangle: -45, tickfont: { size: 9 } },
            yaxis: { tickfont: { size: 9 } },
            height: Math.max(300, genes.length * 22 + 120),
            autosize: true,
          }}
          config={{ responsive: true, displayModeBar: true, toImageButtonOptions: { format: "png", scale: 2 } }}
          style={{ width: "100%" }}
        />
      </div>

      {/* PCA scatter */}
      {Object.keys(pca_coordinates).length > 1 && (
        <div className="card p-4">
          <h3 className="font-semibold text-gray-800 mb-1">PCA of Gene Expression Profiles</h3>
          {pca_variance_explained.length >= 2 && (
            <p className="text-xs text-gray-500 mb-3">
              PC1: {(pca_variance_explained[0] * 100).toFixed(1)}% variance &nbsp;|&nbsp;
              PC2: {(pca_variance_explained[1] * 100).toFixed(1)}% variance
            </p>
          )}
          <Plot
            data={[
              {
                type: "scatter",
                mode: "markers+text",
                x: pcaX,
                y: pcaY,
                text: genes,
                textposition: "top center",
                textfont: { size: 9 },
                marker: { size: 8, color: "#3b82f6", opacity: 0.8 },
              },
            ]}
            layout={{
              margin: { l: 50, r: 20, t: 10, b: 50 },
              xaxis: { title: "PC1" },
              yaxis: { title: "PC2" },
              height: 420,
              autosize: true,
            }}
            config={{ responsive: true, displayModeBar: true, toImageButtonOptions: { format: "png", scale: 2 } }}
            style={{ width: "100%" }}
          />
        </div>
      )}
    </div>
  );
}
