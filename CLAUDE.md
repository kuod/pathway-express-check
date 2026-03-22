# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Pathway Express Check is a bioinformatics web app that interrogates MSigDB gene sets for co-expression coherence in GTEx and other public datasets. Users select a pathway, retrieve median mRNA expression across GTEx tissues via the GTEx Portal REST API, and view heatmaps, a pairwise Pearson correlation matrix, PCA, and summary statistics. Results can be exported as an HTML preprint, Word document, figures ZIP, or Excel workbook.

## Architecture

**Monorepo** with independent `backend/` (Python/FastAPI) and `frontend/` (React/TypeScript/Vite).

### Backend (`backend/`)

- `app/main.py` — FastAPI app with CORS; mounts three routers under `/api`
- `app/services/msigdb.py` — wraps `gseapy` to list/search/fetch MSigDB gene sets; results cached with `@lru_cache`
- `app/services/gtex.py` — async `httpx` client for GTEx Portal API v2; resolves gene symbols → versioned GENCODE IDs, then batch-fetches median TPM in groups of 20
- `app/services/analysis.py` — pure pandas/numpy/scipy computations: correlation matrix, pathway consistency score (mean pairwise Pearson r on log₂(TPM+1)), PCA, summary stats
- `app/routers/pathways.py` — MSigDB library/pathway endpoints
- `app/routers/expression.py` — GTEx tissue list + the primary `/analyze` endpoint (fetches + computes in one call)
- `app/routers/reports.py` — generates HTML (Jinja2 template), DOCX (python-docx), figures ZIP (matplotlib/seaborn), and Excel (openpyxl) exports
- `app/templates/report.html` — Jinja2 preprint HTML template; receives base64-encoded PNGs from the router

### Frontend (`frontend/src/`)

- `api/client.ts` — axios wrapper for all backend calls; `downloadReport()` handles blob download for all export formats
- `hooks/useAnalysis.ts` — central state: selected library/pathway, dataset, result; wraps `useMutation` from TanStack Query
- `pages/Dashboard.tsx` — two-column layout (sidebar + main); orchestrates all components
- `components/PathwaySearch.tsx` — library selector + debounced pathway search list
- `components/ExpressionHeatmap.tsx` — Plotly heatmap of genes × tissues (log₂ TPM+1, viridis)
- `components/CorrelationHeatmap.tsx` — Plotly heatmap (RdBu, −1 to +1) + PCA scatter
- `components/SummaryStats.tsx` — per-gene stats table + top correlated pairs table
- `components/ExportPanel.tsx` — buttons for all four export formats

The Vite dev server proxies `/api/*` to `localhost:8000`, so no CORS issues in development.

## Dev commands

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs available at `http://localhost:8000/docs`.

### Frontend
```bash
cd frontend
npm install
npm run dev        # starts on http://localhost:5173
npm run build      # production build to dist/
npm run lint       # ESLint
```

### Docker (both services)
```bash
docker compose up --build
```

## Key external APIs

- **GTEx Portal v2**: `https://gtexportal.org/api/v2` — no auth required; rate limits are generous but large gene sets (>100 genes) may take 20–40 s
  - `/reference/gene?geneId=<SYMBOL>` — resolve symbol → versioned gencodeId
  - `/expression/medianGeneExpression?datasetId=gtex_v8&gencodeId=<IDs>` — batch up to ~20 IDs per request
  - `/dataset/tissueInfo?datasetId=gtex_v8` — tissue metadata
- **MSigDB via gseapy**: `gp.get_library_name()` / `gp.get_library(name, organism)` — downloads from Broad on first call, then cached in-process

## Notable design decisions

- **Gene symbol resolution**: GTEx requires versioned Ensembl IDs. The gtex service resolves each symbol via `/reference/gene` (parallel async calls) before fetching expression.
- **Pathway consistency score**: single number summarizing co-expression — the mean of all upper-triangle Pearson r values on log₂(TPM+1) data. Useful for comparing pathways.
- **MSigDB cache**: `@lru_cache` on `load_library()` means each library is downloaded once per process. Restart the server to clear.
- **Report figures**: matplotlib figures are rendered server-side to PNG bytes (using the `Agg` backend) and base64-encoded into the HTML report. The same bytes are zipped for the figures export.
- **sklearn dependency**: `analysis.py` uses `sklearn.decomposition.PCA` — if adding new dependencies, remember to add to `requirements.txt`.
