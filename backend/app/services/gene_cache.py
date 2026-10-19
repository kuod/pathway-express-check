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
import os
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).parent.parent / "data" / "gtex_gene_cache.json"
_META_KEY = "_meta"
_cache: dict[str, str] = {}
_loaded: bool = False
_dirty: bool = False
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


def put(symbol: str, gencode_id: str) -> None:
    """Store a symbol -> gencodeId mapping in memory and mark the cache dirty.

    Nothing is written to disk here; call flush() once after a batch of puts.
    """
    global _dirty
    key = symbol.upper()
    with _lock:
        if _cache.get(key) == gencode_id:
            return
        _cache[key] = gencode_id
        _dirty = True


def flush(path: Path = _CACHE_PATH) -> None:
    """Persist the cache if anything changed since the last flush (no-op otherwise)."""
    global _dirty
    with _lock:
        if not _dirty:
            return
        _dirty = False
        _flush(path)


def _flush(path: Path) -> None:
    """Atomically write current cache to disk (must be called with _lock held)."""
    tmp_name = None
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
        # Write to a temp file in the same directory, then rename over the target,
        # so a crash mid-write can never leave a truncated cache file.
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
        tmp_name = None
    except Exception as exc:
        logger.error("Failed to persist gene cache: %s", exc)
    finally:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
