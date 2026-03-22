import type { PathwayDetail } from "@/types";

interface Props {
  pathway: PathwayDetail;
  genesNotFound?: string[];
}

export function GeneList({ pathway, genesNotFound = [] }: Props) {
  const notFoundSet = new Set(genesNotFound);

  return (
    <div className="card p-4">
      <h3 className="font-semibold text-gray-800 mb-1">
        {pathway.name}
        <span className="ml-2 text-xs font-normal text-gray-500">
          {pathway.gene_count} genes
        </span>
      </h3>
      {genesNotFound.length > 0 && (
        <p className="text-xs text-amber-600 mb-2">
          {genesNotFound.length} gene(s) not found in GTEx and excluded from analysis.
        </p>
      )}
      <div className="flex flex-wrap gap-1 max-h-36 overflow-y-auto">
        {pathway.genes.map((gene) => (
          <span
            key={gene}
            className={`px-1.5 py-0.5 rounded text-xs font-mono ${
              notFoundSet.has(gene)
                ? "bg-red-100 text-red-600 line-through"
                : "bg-blue-100 text-blue-800"
            }`}
          >
            {gene}
          </span>
        ))}
      </div>
    </div>
  );
}
