"""
GTEx Portal API v2 client.
Docs: https://gtexportal.org/api/v2/redoc

Key design decisions:
- All HTTP calls are async via httpx
- Gene symbols are resolved to versioned Ensembl IDs via /reference/gene
- Expression is fetched in batches of 20 genes to stay within URL length limits
- Tissue info is cached per process
"""

import asyncio
import logging
from functools import lru_cache
import httpx
from app.config import settings
from app.services import gene_cache

logger = logging.getLogger(__name__)


_BASE = settings.gtex_api_base
_TIMEOUT = settings.request_timeout
_GENE_BATCH_SIZE = 20
_RESOLVE_CONCURRENCY = 20  # cap simultaneous /reference/gene requests


async def resolve_genes(symbols: list[str]) -> dict[str, str | None]:
    """
    Resolve gene symbols to versioned GTEx gencodeIds (ENSG....version).
    Returns {symbol: gencodeId_or_None}.
    Unknown symbols map to None.

    Checks the local disk cache first; only symbols not in cache hit the API.
    Successful API resolutions are written back to the cache.
    """
    results: dict[str, str | None] = {}
    uncached: list[str] = []

    for sym in symbols:
        cached = gene_cache.lookup(sym)
        if cached is not None:
            results[sym] = cached
        else:
            uncached.append(sym)

    if not uncached:
        logger.info("Gene resolution: %d/%d from cache (0 API calls)", len(results), len(symbols))
        return results

    logger.info(
        "Gene resolution: %d/%d from cache, %d need API",
        len(results), len(symbols), len(uncached),
    )
    sem = asyncio.Semaphore(_RESOLVE_CONCURRENCY)

    async def fetch_one(client: httpx.AsyncClient, symbol: str):
        async with sem:
            try:
                r = await client.get(
                    f"{_BASE}/reference/gene",
                    params={"geneId": symbol, "gencodeVersion": "v26", "genomeBuild": "GRCh38/hg38"},
                    timeout=_TIMEOUT,
                )
                r.raise_for_status()
                data = r.json()
                genes = data.get("data", [])
                if genes:
                    gid = genes[0].get("gencodeId")
                    results[symbol] = gid
                    if gid:
                        gene_cache.put(symbol, gid)  # write-back
                else:
                    results[symbol] = None
            except Exception as exc:
                logger.warning("Failed to resolve gene symbol %r: %s", symbol, exc)
                results[symbol] = None

    logger.info("Resolving %d gene symbols via GTEx API…", len(uncached))
    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[fetch_one(client, s) for s in uncached])

    found = sum(1 for v in results.values() if v)
    logger.info("Gene resolution complete: %d/%d symbols matched", found, len(symbols))
    return results


async def fetch_median_expression(
    gencode_ids: list[str],
    dataset_id: str = "gtex_v8",
    tissue_ids: list[str] | None = None,
) -> list[dict]:
    """
    Fetch median gene expression across GTEx tissues.
    Returns raw list of records from the API:
      [{gencodeId, geneSymbol, tissueSiteDetailId, median, unit}, ...]
    """
    all_records: list[dict] = []

    async def fetch_batch(client: httpx.AsyncClient, batch: list[str]):
        params: dict = {
            "datasetId": dataset_id,
            "gencodeId": batch,  # list → httpx repeats the key: ?gencodeId=X&gencodeId=Y
        }
        if tissue_ids:
            params["tissueSiteDetailId"] = ",".join(tissue_ids)
        try:
            r = await client.get(
                f"{_BASE}/expression/medianGeneExpression",
                params=params,
                timeout=_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            all_records.extend(data.get("data", []))
        except Exception as exc:
            logger.warning("Expression batch fetch failed for %d IDs: %s", len(batch), exc)

    batches = [
        gencode_ids[i : i + _GENE_BATCH_SIZE]
        for i in range(0, len(gencode_ids), _GENE_BATCH_SIZE)
    ]
    logger.info(
        "Fetching median expression: %d genes across %d batches (dataset=%s)",
        len(gencode_ids),
        len(batches),
        dataset_id,
    )

    async def fetch_batch_logged(client: httpx.AsyncClient, batch: list[str], idx: int):
        logger.info("  Batch %d/%d — %d IDs", idx + 1, len(batches), len(batch))
        await fetch_batch(client, batch)

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*[fetch_batch_logged(client, b, i) for i, b in enumerate(batches)])

    return all_records


async def list_tissues(dataset_id: str = "gtex_v8") -> list[dict]:
    """
    Return list of tissue metadata dicts from GTEx.
    Each dict has: tissueSiteDetailId, tissueSiteDetail, tissueSite, colorHex.
    """
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_BASE}/dataset/tissueSiteDetail",
            timeout=_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])


async def get_expression_matrix(
    symbols: list[str],
    dataset_id: str = "gtex_v8",
    tissue_ids: list[str] | None = None,
) -> tuple[dict[str, dict[str, float]], list[str], list[str]]:
    """
    High-level: resolve symbols → fetch expression → build matrix.

    Returns:
        matrix: {gene_symbol: {tissue_id: median_tpm}}
        genes_found: symbols that had GTEx entries
        genes_not_found: symbols that could not be resolved
    """
    # Step 1: resolve symbols to Ensembl IDs
    id_map = await resolve_genes(symbols)
    found_map = {sym: gid for sym, gid in id_map.items() if gid}
    genes_not_found = [sym for sym, gid in id_map.items() if not gid]

    if not found_map:
        return {}, [], genes_not_found

    # Step 2: fetch expression in batches
    gencode_ids = list(found_map.values())
    records = await fetch_median_expression(gencode_ids, dataset_id, tissue_ids)

    # Step 3: build reverse map gencodeId -> symbol
    rev_map = {gid: sym for sym, gid in found_map.items()}

    # Step 4: pivot into matrix
    matrix: dict[str, dict[str, float]] = {}
    for rec in records:
        gid = rec.get("gencodeId", "")
        # GTEx returns the versioned ID; rev_map keys are versioned too
        sym = rev_map.get(gid)
        if not sym:
            # Try matching by base ID (without version suffix)
            base = gid.rsplit(".", 1)[0]
            sym = next((s for s, g in found_map.items() if g.startswith(base)), None)
        if sym:
            tissue = rec.get("tissueSiteDetailId", "")
            tpm = float(rec.get("median", 0.0))
            matrix.setdefault(sym, {})[tissue] = tpm

    genes_found = list(matrix.keys())
    genes_not_found_final = genes_not_found + [
        sym for sym in found_map if sym not in matrix
    ]

    tissue_count = len({t for g in matrix.values() for t in g})
    logger.info(
        "Expression matrix built: %d genes × %d tissues", len(genes_found), tissue_count
    )
    return matrix, genes_found, genes_not_found_final
