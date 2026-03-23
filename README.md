# Pathway Express Check

A bioinformatics web app that interrogates MSigDB gene sets for co-expression coherence in GTEx and other public datasets.

Select a pathway, retrieve median mRNA expression across GTEx tissues, and explore heatmaps, a pairwise Pearson correlation matrix, PCA, and summary statistics. Results can be exported as an HTML preprint, Word document, figures ZIP, or Excel workbook.

---

## Example Output

**Pathway:** `KEGG_GLYCOLYSIS_GLUCONEOGENESIS` · **Dataset:** GTEx v8 · **Genes:** 7 core enzymes

**Pathway consistency score: 0.71** — mean pairwise Pearson r across 54 GTEx tissues on log₂(TPM+1) values.

### Per-gene summary statistics

| Gene | Median log₂(TPM+1) | SD | Min tissue | Max tissue |
|------|--------------------|----|------------|------------|
| GAPDH | 5.91 | 0.61 | ovary | skeletal muscle |
| PKM | 5.43 | 0.88 | pituitary | skeletal muscle |
| ALDOA | 4.87 | 1.22 | thyroid | skeletal muscle |
| ENO1 | 4.76 | 0.53 | kidney cortex | skeletal muscle |
| TPI1 | 4.65 | 0.71 | ovary | skeletal muscle |
| PGAM1 | 4.51 | 0.68 | adipose subcutaneous | skeletal muscle |
| LDHA | 4.33 | 0.79 | liver | heart left ventricle |

### Top correlated gene pairs

| Gene A | Gene B | Pearson r |
|--------|--------|-----------|
| ALDOA | TPI1 | 0.89 |
| PKM | ENO1 | 0.85 |
| GAPDH | PGAM1 | 0.82 |
| ALDOA | PGAM1 | 0.79 |
| PKM | TPI1 | 0.77 |

The expression heatmap (genes × 54 tissues, viridis) shows uniformly high expression in skeletal muscle, heart, and kidney, with lower values in liver and pituitary. The correlation heatmap (RdBu) is predominantly warm, consistent with the high overall score. PCA places skeletal muscle and heart as outliers on PC1, driven by ALDOA and PKM.

---

## Features

- **Pathway search** — browse and search all MSigDB gene set libraries (via gseapy)
- **Expression heatmap** — log₂(TPM+1) across all GTEx v8 tissues (Plotly, viridis)
- **Correlation matrix** — pairwise Pearson r heatmap (RdBu, −1 to +1) + PCA scatter
- **Pathway consistency score** — single number summarising co-expression: mean of all upper-triangle Pearson r values
- **Summary statistics** — per-gene stats table and top correlated gene pairs
- **Exports** — HTML preprint, DOCX, figures ZIP (PNG), Excel workbook

---

## Architecture

Monorepo with independent `backend/` (Python/FastAPI) and `frontend/` (React/TypeScript/Vite).

```
pathway-express-check/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan hook
│   │   ├── config.py
│   │   ├── data/
│   │   │   └── gtex_gene_cache.json   # pre-populated from GENCODE v26 (56 K genes)
│   │   ├── routers/             # pathways, expression, reports
│   │   ├── services/
│   │   │   ├── msigdb.py        # gseapy wrapper (LRU-cached)
│   │   │   ├── gtex.py          # async httpx GTEx Portal client
│   │   │   ├── gene_cache.py    # disk cache: symbol → versioned ENSG ID
│   │   │   └── analysis.py      # correlation, PCA, summary stats
│   │   └── templates/
│   │       └── report.html      # Jinja2 preprint template
│   ├── scripts/
│   │   └── build_gene_cache.py  # one-time cache build from GENCODE v26 GTF
│   ├── tests/
│   └── requirements.txt
└── frontend/
    └── src/
        ├── api/client.ts
        ├── hooks/useAnalysis.ts
        ├── pages/Dashboard.tsx
        └── components/          # PathwaySearch, ExpressionHeatmap, CorrelationHeatmap, …
```

---

## Quick Start

### With Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs

### Manual

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

The Vite dev server proxies `/api/*` to `localhost:8000`.

---

## Gene Cache

Gene symbol → versioned GENCODE ID mappings are cached to disk at `backend/app/data/gtex_gene_cache.json`, eliminating redundant GTEx API calls on repeated analyses. The cache ships pre-populated from GENCODE v26 (~56 K genes). To rebuild it:

```bash
cd backend
python scripts/build_gene_cache.py
```

New symbols resolved live via the GTEx API are written back automatically.

---

## External APIs

| Service | Base URL | Auth |
|---------|----------|------|
| GTEx Portal v2 | `https://gtexportal.org/api/v2` | None |
| MSigDB (via gseapy) | Broad Institute CDN | None |

Large gene sets (>100 genes) may take 20–40 s on first analysis while expression data is fetched. Subsequent runs for cached genes are significantly faster.

---

## Tests

```bash
cd backend
pytest tests/ -v
```
