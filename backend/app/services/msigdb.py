"""
MSigDB service using gseapy to fetch pathway gene sets.
Results are cached in-process to avoid repeated network downloads.
"""

import logging
import gseapy as gp
from functools import lru_cache
from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def list_libraries() -> list[str]:
    """Return all available MSigDB library names for the configured organism."""
    return sorted(gp.get_library_name(organism=settings.msigdb_organism))


@lru_cache(maxsize=32)
def load_library(library_name: str) -> dict[str, list[str]]:
    """
    Load a full MSigDB library. Returns {pathway_name: [gene, ...]} dict.
    Cached so each library is only downloaded once per process.
    """
    logger.info("Fetching MSigDB library '%s' from Broad…", library_name)
    result = gp.get_library(name=library_name, organism=settings.msigdb_organism)
    logger.info("MSigDB library '%s' loaded: %d gene sets", library_name, len(result))
    return result


def search_pathways(library_name: str, query: str = "", max_results: int = 50) -> list[dict]:
    """
    Search pathways within a library by name substring (case-insensitive).
    Returns list of {name, gene_count} dicts sorted by name.
    """
    gene_sets = load_library(library_name)
    query_lower = query.lower()
    results = [
        {"name": name, "gene_count": len(genes)}
        for name, genes in gene_sets.items()
        if query_lower in name.lower()
    ]
    results.sort(key=lambda x: x["name"])
    return results[:max_results]


def get_pathway_genes(library_name: str, pathway_name: str) -> list[str]:
    """Return the gene list for a specific pathway. Raises KeyError if not found."""
    gene_sets = load_library(library_name)
    if pathway_name not in gene_sets:
        raise KeyError(f"Pathway '{pathway_name}' not found in library '{library_name}'")
    genes = gene_sets[pathway_name]
    logger.info("Pathway '%s' retrieved: %d genes", pathway_name, len(genes))
    return genes
