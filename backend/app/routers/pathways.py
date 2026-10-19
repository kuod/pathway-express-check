from fastapi import APIRouter, HTTPException, Query
from app.services import msigdb

router = APIRouter()


def _require_library(library: str) -> None:
    """404 for an unknown library instead of a 500 with a raw gseapy exception."""
    try:
        known = msigdb.list_libraries()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not list MSigDB libraries: {e}")
    if library not in known:
        raise HTTPException(status_code=404, detail=f"Unknown MSigDB library '{library}'")


@router.get("/libraries")
def get_libraries() -> list[str]:
    """List all available MSigDB library names."""
    return msigdb.list_libraries()


@router.get("/search")
def search_pathways(
    library: str = Query(..., description="MSigDB library name, e.g. HALLMARK_2020"),
    query: str = Query("", description="Substring to filter pathway names"),
    max_results: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """Search for pathways within a MSigDB library."""
    _require_library(library)
    try:
        return msigdb.search_pathways(library, query, max_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{library}/{pathway_name}")
def get_pathway(library: str, pathway_name: str) -> dict:
    """Return gene list for a specific pathway."""
    _require_library(library)
    try:
        genes = msigdb.get_pathway_genes(library, pathway_name)
        return {"name": pathway_name, "library": library, "genes": genes, "gene_count": len(genes)}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
