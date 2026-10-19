# ISSUES

Findings from an adversarial pass (no GitHub remote, so tracked here). Branch: `adversarial-pass/audit-fixes`.
Each fix commit references its issue number. Status values: open / fixed / wontfix-documented.

Baseline evidence: `pytest` (23 tests, all gtex.py) passed on Python 3.13; `npm run build` FAILED; `npm run lint` FAILED.

---

## #1 bug: GTEx expression results silently truncated at 250 records per request
- Repro: `GET /expression/medianGeneExpression?datasetId=gtex_v8&gencodeId=<20 ids>` returns `data` of 250 rows with `paging_info: {numberOfPages: 5, totalNumberOfItems: 1080}`. `fetch_median_expression` reads only page 0, so a 20-gene batch (up to 1080 rows) loses ~75% of its data. Genes then appear "not found" or have missing tissues (filled with 0 downstream), corrupting every correlation.
- Fix: request `itemsPerPage=2000` and follow `paging_info.numberOfPages`.
- Status: fixed

## #2 bug: `tissue_ids` filter is sent comma-joined and rejected by GTEx
- Repro: `...&tissueSiteDetailId=Liver,Lung` -> 422 enum error; `...&tissueSiteDetailId=Liver&tissueSiteDetailId=Lung` -> 2 rows. The 422 is swallowed (see #4), yielding an empty result.
- Fix: pass a list so httpx repeats the key.
- Status: fixed

## #3 bug: "GTEx v10" is offered in the UI but gene resolution is hard-coded to GENCODE v26 (and the v26 disk cache)
- Repro: v26 id `ENSG00000141510.16` with `datasetId=gtex_v10` returns `data: []`. v10 uses GENCODE v39 (TP53 -> `.18`). Selecting GTEx v10 therefore always ends in 404 "No GTEx expression data".
- Fix: map dataset -> GENCODE version, use cache only for v26 datasets, reject unknown dataset ids with 400. (The v10 -> v39 mapping was confirmed against the live API for TP53 only; flagged for owner review.)
- Status: fixed

## #4 bug: failed expression batches are swallowed; genes are mis-reported as "not found"
- Repro: any HTTP error in a batch (422, timeout, 5xx) is logged and ignored; if every batch fails the API answers 404 "No GTEx expression data found" rather than 502.
- Fix: raise when all batches fail so the router returns 502 with the cause.
- Status: fixed

## #5 bug: `/analyze` returns 500 for a single resolved gene or a single tissue
- Repro: `run_full_analysis({"A": {"x": 1, "y": 2}})` -> consistency score NaN -> `ValueError: Out of range float values are not JSON compliant`. Two genes x one tissue gives NaN std. A pathway where only one gene resolves is realistic.
- Fix: router returns 422 with a clear message when fewer than 2 genes have data; NaN std becomes 0.
- Status: fixed

## #6 bug: Content-Disposition filename built from unsanitised pathway name
- Repro: `pathway_name = 'a"b\r\nX: y'` or non-latin-1 characters -> broken/injectable header, server error for non-latin-1 names. Only spaces were replaced.
- Fix: `_safe_filename()` keeps `[A-Za-z0-9._-]`.
- Status: fixed

## #7 bug: `npm run build` fails (TypeScript errors), so `docker compose up --build` cannot build the frontend
- Repro: `cd frontend && npm install && npm run build` -> 3x TS2769 (`colorbar.title` string, `mode: "markers+text"`) in ExpressionHeatmap/CorrelationHeatmap with @types/plotly.js 2.35.
- Fix: `title: { text: ... }`, correct mode literal.
- Status: fixed

## #8 bug: `npm run lint` is non-functional
- Repro: ESLint 9 has no config file (`eslint.config.js` missing) and the script uses the removed `--ext` flag.
- Fix: add flat config with typescript-eslint + react-hooks, fix script, fix findings.
- Status: fixed

## #9 bug: changing the dataset keeps the previous dataset's results, which can then be exported mislabelled
- Repro: run analysis on GTEx v8, switch dropdown to v10: charts and Export panel remain, with `dataset_info` set to the new label.
- Fix: clear `result` in `setDatasetId`.
- Status: fixed

## #10 bug: PathwaySearch fires a request per keystroke (docs claim debounced) and `handleSelect` has no error handling
- Repro: type in filter box -> one request per character; if `/pathways/{lib}/{name}` fails (network, 500) the rejection is unhandled and the UI gives no feedback.
- Fix: 300 ms debounce, try/catch with toast.
- Status: fixed

## #11 bug: build_gene_cache.py lets chrY PAR genes overwrite the chrX/autosomal ID
- Repro: GENCODE lists pseudo-autosomal genes twice with the same `gene_name`, the Y copy having id `ENSG....N_PAR_Y`; last record wins so symbols (e.g. SHOX, IL3RA, CSF2RA) map to `_PAR_Y` ids which GTEx does not serve.
- Fix: skip ids ending `_PAR_Y`.
- Status: fixed

## #12 bug: `clean.sh --force` overwrites the git-tracked gene cache with `{}`
- Evidence: the working tree of this repo is currently in exactly that state (`gtex_gene_cache.json` shows -810 lines modified), leaving a dirty tree and destroying shipped data. Note also that HEAD's clean.sh uses `mapfile` / `declare -A` (bash 4+) and fails on macOS /bin/bash 3.2; the owner's uncommitted working-tree change already addresses that and was NOT touched or duplicated here (expect a small merge conflict in clean.sh).
- Fix: restore the cache from git (`git checkout --`) when available, else leave it alone; dry-run text updated.
- Status: fixed

## #13 bug: nginx default `proxy_read_timeout` (60 s) is shorter than the documented analysis time and the 120 s axios timeout
- Repro: docker deployment, large pathway -> 504 from nginx while the backend is still working.
- Fix: `proxy_read_timeout 300s`; also `client_max_body_size 50m` since nginx's 1 MB default rejects report POSTs carrying large result matrices (not reproduced under docker here; no docker daemon used).
- Status: fixed

## #14 bug: `GTEX_DATASET_ID` setting / `.env.example` has no effect
- Repro: `settings.gtex_dataset_id` is never read; `ExpressionRequest.dataset_id` default is hard-coded "gtex_v8".
- Fix: schema default reads from settings.
- Status: fixed

## #15 bug: pathway search validation (`max_results=0`, unknown library -> 500)
- Repro: `/api/pathways/search?library=nope` -> 500 with raw exception text; `max_results=0` / negative accepted (negative slices off the end).
- Fix: `ge=1`; unknown library -> 404.
- Status: fixed

## #16 documentation: stale or wrong docs
- README claims the shipped cache has ~56K genes; committed file has 799. README "Example output" shows SD / "Min tissue" columns the app never computes, and numbers that cannot be reproduced from the code (treat as illustrative; labelled so now). ExportPanel says figures are 300 dpi; backend renders 150 dpi. DOCX methods claim "only protein-coding genes" which the code does not enforce. CLAUDE.md says search is debounced (was not, see #10) and lists the dead `/dataset/tissueInfo` endpoint (code uses `tissueSiteDetail`). docker-compose comment says "hot-reload" but uvicorn runs without `--reload`. README test command needs pytest + pytest-asyncio which were not in any requirements file.
- Fix: corrected each (CLAUDE.md debounce claim is now true after #10).
- Status: fixed

## #17 enhancement: test coverage limited to gtex.py; pytest not installable from repo files
- Evidence: no tests for analysis.py, routers, reports, gene_cache; no dev requirements.
- Fix: `requirements-dev.txt`, tests for analysis edge cases, router errors, filename sanitising, pagination, gencode mapping, PAR_Y filter.
- Status: fixed (minimal; reports/msigdb remain lightly covered)

## #18 enhancement: unused Python dependencies
- Evidence: `kaleido`, `plotly`, `python-multipart` are in requirements.txt but never imported (kaleido 0.2.1 is also a heavy, platform-sensitive wheel).
- Fix: removed.
- Status: fixed

## #19 bug (design): missing gene/tissue values are silently zero-filled before correlation
- Evidence: `build_dataframe` does `fillna(0.0)`; with a tissue subset or incomplete GTEx rows the Pearson r is computed on fabricated zeros (sparse example gives different scores).
- Proposed fix: drop tissues with any missing value (or pairwise-complete correlation) and report it. Behaviour change affects results, so left for owner decision.
- Status: open

## #20 enhancement: concurrency and I/O hazards
- `reports.py` uses global `matplotlib.pyplot` state from sync endpoints that run in a thread pool: concurrent exports can interleave figures. Proposed: use `matplotlib.figure.Figure` objects directly.
- `gene_cache.put` rewrites the whole (potentially 3 MB) JSON file synchronously, inside the event loop, once per newly resolved symbol; and it writes into the git-tracked data file. Proposed: batch flush / write to a separate untracked file.
- Frontend: results from an in-flight analysis can land after the user selected a different pathway (mutation reads state at call time, sets `result` unconditionally).
- Status: open

## #21 enhancement: dependency drift and vulnerabilities
- `npm audit --omit=dev`: 14 vulnerabilities (2 critical, 8 high) from the plotly.js / transitive tree. Python deps use open `>=` ranges with no lockfile (numpy>=2, pandas>=2.2, gseapy>=1.1.12), Docker uses Python 3.11 while local runs were on 3.13.
- Proposed: pin/lock Python deps, review `npm audit` (some fixes are breaking). Not changed: risk of breaking the plotting stack.
- Status: open

## Checked, no finding
- Secrets: no keys/tokens in tree or history (`git log --all` file names and grep); `.env` is git-ignored; only author identity in history.
- Jinja2 report: autoescape on, no `|safe` use; pathway name XSS not reproducible.
