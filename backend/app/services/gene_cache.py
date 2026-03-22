"""
Persistent disk cache for gene symbol → versioned GENCODE ID mappings.

The mapping is stable for a fixed dataset/GENCODE version (GTEx v8 / GENCODE v26),
so it is safe to cache permanently on disk and reuse across server restarts.

Usage:
    gene_cache.load()          # call once at startup
    gid = gene_cache.lookup("TP53")    # returns str or None
    gene_cache.put("TP53", "ENSG00000141510.16")  # write-back after API hit
"""

import json
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).parent.parent / "data" / "gtex_gene_cache.json"
_META_KEY = "_meta"
_cache: dict[str, str] = {}
_loaded: bool = False
_lock = threading.Lock()


def load(path: Path = _CACHE_PATH) -> None:
    """Load the cache from disk. Idempotent — subsequent calls are no-ops."""
    global _cache, _loaded
    with _lock:
        if _loaded:
            return
        if not path.exists():
            logger.warning("Gene cache not found at %s — API fallback active", path)
            _loaded = True
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            _cache = {k: v for k, v in raw.items() if k != _META_KEY and isinstance(v, str)}
            logger.info("Gene cache loaded: %d symbols", len(_cache))
        except Exception as exc:
            logger.error("Failed to load gene cache: %s", exc)
        _loaded = True


def lookup(symbol: str) -> str | None:
    """Return cached gencodeId for *symbol*, or None if not cached."""
    if not _loaded:
        load()
    return _cache.get(symbol.upper())


def put(symbol: str, gencode_id: str, path: Path = _CACHE_PATH) -> None:
    """Store a symbol → gencodeId mapping and persist to disk."""
    key = symbol.upper()
    with _lock:
        if _cache.get(key) == gencode_id:
            return
        _cache[key] = gencode_id
        _flush(path)


def _flush(path: Path) -> None:
    """Write current cache to disk (must be called with _lock held)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing_meta: dict = {}
        if path.exists():
            try:
                existing_meta = json.loads(path.read_text(encoding="utf-8")).get(_META_KEY, {})
            except Exception:
                pass
        out: dict = ({_META_KEY: existing_meta} if existing_meta else {})
        out.update(_cache)
        path.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to persist gene cache: %s", exc)
