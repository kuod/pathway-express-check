"""Unit tests for app/services/analysis.py, including degenerate inputs."""

import json

import pytest

from app.services import analysis


def _dumps(result):
    # The API serialises with allow_nan=False semantics; NaN must never leak out.
    return json.dumps(result, allow_nan=False)


def test_perfectly_correlated_genes_score_one():
    m = {"A": {"t1": 1.0, "t2": 3.0, "t3": 7.0}, "B": {"t1": 2.0, "t2": 6.0, "t3": 14.0}}
    r = analysis.run_full_analysis(m)
    assert r["pathway_consistency_score"] > 0.9
    _dumps(r)


def test_anticorrelated_genes_negative_score():
    m = {"A": {"t1": 1.0, "t2": 100.0}, "B": {"t1": 100.0, "t2": 1.0}}
    assert analysis.run_full_analysis(m)["pathway_consistency_score"] == pytest.approx(-1.0)


def test_constant_gene_does_not_produce_nan():
    m = {"A": {"t1": 1.0, "t2": 1.0, "t3": 1.0}, "B": {"t1": 2.0, "t2": 5.0, "t3": 1.0}}
    _dumps(analysis.run_full_analysis(m))


def test_single_tissue_has_finite_stats():
    m = {"A": {"t1": 1.0}, "B": {"t1": 2.0}}
    r = analysis.run_full_analysis(m)
    assert r["summary_stats"]["A"]["std_tpm"] == 0.0
    _dumps(r)


def test_top_pairs_sorted_desc():
    m = {
        "A": {"t1": 1.0, "t2": 2.0, "t3": 3.0},
        "B": {"t1": 1.0, "t2": 2.0, "t3": 3.1},
        "C": {"t1": 3.0, "t2": 2.0, "t3": 1.0},
    }
    pairs = analysis.run_full_analysis(m)["top_correlated_pairs"]
    rs = [p["pearson_r"] for p in pairs]
    assert rs == sorted(rs, reverse=True)
    assert len(pairs) == 3


def test_single_gene_score_is_nan_so_router_must_guard():
    """Documents why /analyze rejects <2 genes (NaN is not JSON-serialisable)."""
    r = analysis.run_full_analysis({"A": {"t1": 1.0, "t2": 2.0}})
    assert r["pathway_consistency_score"] != r["pathway_consistency_score"]
