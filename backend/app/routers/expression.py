import logging
import time

from fastapi import APIRouter, HTTPException
from app.models.schemas import ExpressionRequest, AnalysisResponse
from app.services import gtex, analysis

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tissues")
async def get_tissues(dataset_id: str = "gtex_v8") -> list[dict]:
    """Return all GTEx tissue metadata for a dataset."""
    try:
        return await gtex.list_tissues(dataset_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GTEx API error: {e}")


@router.post("/analyze")
async def analyze(request: ExpressionRequest) -> AnalysisResponse:
    """
    Fetch GTEx median expression for a gene list, then run co-expression analysis.
    This is the primary endpoint the frontend calls after selecting a pathway.
    """
    if not request.genes:
        raise HTTPException(status_code=400, detail="Gene list cannot be empty")

    logger.info(
        "Analysis request: pathway='%s', genes=%d, dataset=%s",
        request.pathway_name or "unnamed",
        len(request.genes),
        request.dataset_id,
    )
    t_start = time.perf_counter()

    # Fetch expression from GTEx
    try:
        matrix, genes_found, genes_not_found = await gtex.get_expression_matrix(
            symbols=request.genes,
            dataset_id=request.dataset_id,
            tissue_ids=request.tissue_ids,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GTEx API error: {e}")

    if not matrix:
        raise HTTPException(
            status_code=404,
            detail="No GTEx expression data found for any of the provided genes.",
        )

    all_tissue_keys: set[str] = set()
    for gene_tissues in matrix.values():
        all_tissue_keys.update(gene_tissues.keys())
    tissues = sorted(all_tissue_keys)

    logger.info(
        "GTEx fetch done: %d/%d genes matched, %d tissues",
        len(genes_found),
        len(request.genes),
        len(tissues),
    )

    expression = {
        "genes_found": genes_found,
        "genes_not_found": genes_not_found,
        "tissues": tissues,
        "expression_matrix": matrix,
    }

    # Run co-expression analysis
    coexpression = analysis.run_full_analysis(matrix)

    elapsed = time.perf_counter() - t_start
    logger.info(
        "Analysis complete: consistency_score=%.4f, elapsed=%.1fs",
        coexpression.get("pathway_consistency_score", float("nan")),
        elapsed,
    )

    return AnalysisResponse(expression=expression, coexpression=coexpression)
