"""
One-time script to pre-populate the gene symbol → GENCODE ID cache.

Streams the GENCODE v26 annotation GTF (the same annotation GTEx v8 uses),
extracts gene-level records, and writes symbol → versioned ENSG ID mappings to
backend/app/data/gtex_gene_cache.json.

Only "gene" feature lines are parsed; transcript/exon lines are skipped, so the
full ~1 GB uncompressed GTF is processed efficiently in a single streaming pass.

Usage:
    cd backend
    python scripts/build_gene_cache.py
"""

import gzip
import json
import logging
import re
import sys
import urllib.request
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# GENCODE v26 — the gene annotation GTEx v8 is built on
_SOURCE_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_26/"
    "gencode.v26.annotation.gtf.gz"
)
_OUT_PATH = Path(__file__).parent.parent / "app" / "data" / "gtex_gene_cache.json"

_RE_GENE_ID = re.compile(r'gene_id "([^"]+)"')
_RE_GENE_NAME = re.compile(r'gene_name "([^"]+)"')


def build() -> None:
    logger.info("Downloading GENCODE v26 annotation GTF (~37 MB)…")
    logger.info("  %s", _SOURCE_URL)

    try:
        with urllib.request.urlopen(_SOURCE_URL, timeout=120) as resp:
            compressed = resp.read()
    except Exception as exc:
        logger.error("Download failed: %s", exc)
        sys.exit(1)

    logger.info("Download complete (%.1f MB). Parsing gene records…", len(compressed) / 1e6)

    cache: dict[str, str] = {}
    skipped = 0
    try:
        with gzip.open(BytesIO(compressed), "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                fields = line.split("\t", 3)
                if len(fields) < 4 or fields[2] != "gene":
                    continue
                attrs = fields[3]
                gid_m = _RE_GENE_ID.search(attrs)
                sym_m = _RE_GENE_NAME.search(attrs)
                if not gid_m or not sym_m:
                    skipped += 1
                    continue
                gencode_id = gid_m.group(1)   # e.g. ENSG00000227232.5
                symbol = sym_m.group(1).upper()  # e.g. WASH7P
                cache[symbol] = gencode_id
    except Exception as exc:
        logger.error("Failed to parse GTF: %s", exc)
        sys.exit(1)

    logger.info(
        "Parsed %d gene symbol → gencodeId mappings (%d records skipped).",
        len(cache), skipped,
    )

    meta = {
        "gtex_dataset": "gtex_v8",
        "gencode_version": "v26",
        "genome_build": "GRCh38/hg38",
        "source": _SOURCE_URL,
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gene_count": len(cache),
    }
    out: dict = {"_meta": meta}
    out.update(cache)

    _OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OUT_PATH.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")
    logger.info("Wrote cache to %s", _OUT_PATH)


if __name__ == "__main__":
    build()
