import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchLibraries, searchPathways, fetchPathway } from "@/api/client";
import type { PathwayDetail } from "@/types";

interface Props {
  selectedLibrary: string;
  onLibraryChange: (lib: string) => void;
  onPathwaySelect: (pathway: PathwayDetail) => void;
}

export function PathwaySearch({ selectedLibrary, onLibraryChange, onPathwaySelect }: Props) {
  const [query, setQuery] = useState("");

  const { data: libraries = [], isLoading: loadingLibs } = useQuery({
    queryKey: ["libraries"],
    queryFn: fetchLibraries,
  });

  const { data: pathways = [], isLoading: loadingPathways } = useQuery({
    queryKey: ["pathways", selectedLibrary, query],
    queryFn: () => searchPathways(selectedLibrary, query, 100),
    enabled: !!selectedLibrary,
  });

  async function handleSelect(name: string) {
    const detail = await fetchPathway(selectedLibrary, name);
    onPathwaySelect(detail);
  }

  return (
    <div className="card p-4 space-y-3">
      <h2 className="font-semibold text-gray-800">1. Select Pathway</h2>

      {/* Library selector */}
      <div>
        <label className="block text-xs text-gray-500 mb-1">MSigDB Library</label>
        <select
          className="select"
          value={selectedLibrary}
          onChange={(e) => onLibraryChange(e.target.value)}
          disabled={loadingLibs}
        >
          <option value="">— choose library —</option>
          {libraries.map((lib) => (
            <option key={lib} value={lib}>
              {lib}
            </option>
          ))}
        </select>
      </div>

      {/* Pathway search */}
      {selectedLibrary && (
        <div>
          <label className="block text-xs text-gray-500 mb-1">Search Pathways</label>
          <input
            className="input"
            placeholder="Filter by name…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      )}

      {/* Pathway list */}
      {selectedLibrary && (
        <div className="max-h-64 overflow-y-auto border border-gray-200 rounded text-sm">
          {loadingPathways ? (
            <p className="p-3 text-gray-400">Loading…</p>
          ) : pathways.length === 0 ? (
            <p className="p-3 text-gray-400">No results.</p>
          ) : (
            <ul>
              {pathways.map((pw) => (
                <li
                  key={pw.name}
                  className="flex justify-between items-center px-3 py-2 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-0"
                  onClick={() => handleSelect(pw.name)}
                >
                  <span className="truncate pr-2">{pw.name}</span>
                  <span className="text-xs text-gray-400 shrink-0">{pw.gene_count} genes</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
