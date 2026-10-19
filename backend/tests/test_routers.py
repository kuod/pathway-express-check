"""API-level tests with the GTEx/MSigDB services mocked."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _post(genes, dataset="gtex_v8"):
    return client.post(
        "/api/expression/analyze",
        json={"genes": genes, "pathway_name": "P", "dataset_id": dataset},
    )


def test_analyze_empty_genes_400():
    assert _post([]).status_code == 400


def test_analyze_unknown_dataset_400():
    assert _post(["A", "B"], dataset="gtex_v99").status_code == 400


def test_analyze_single_gene_is_422_not_500():
    with patch(
        "app.services.gtex.get_expression_matrix",
        AsyncMock(return_value=({"A": {"t1": 1.0, "t2": 2.0}}, ["A"], ["B"])),
    ):
        r = _post(["A", "B"])
    assert r.status_code == 422
    assert "at least 2 genes" in r.json()["detail"]


def test_analyze_gtex_failure_is_502():
    with patch("app.services.gtex.get_expression_matrix", AsyncMock(side_effect=RuntimeError("boom"))):
        assert _post(["A", "B"]).status_code == 502


def test_analyze_happy_path():
    matrix = {"A": {"t1": 1.0, "t2": 5.0, "t3": 9.0}, "B": {"t1": 2.0, "t2": 6.0, "t3": 10.0}}
    with patch(
        "app.services.gtex.get_expression_matrix", AsyncMock(return_value=(matrix, ["A", "B"], []))
    ):
        r = _post(["A", "B"])
    assert r.status_code == 200
    assert r.json()["coexpression"]["pathway_consistency_score"] > 0.9


def test_dataset_default_comes_from_settings():
    from app.config import settings
    from app.models.schemas import ExpressionRequest

    assert ExpressionRequest(genes=["A"], pathway_name="p").dataset_id == settings.gtex_dataset_id
