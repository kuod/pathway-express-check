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


# ---- missing-value handling (ISSUES.md #19): never zero-filled ----------------

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

NAN = float("nan")


def _df(rows):
    return analysis.build_dataframe(rows)


def test_build_dataframe_keeps_nan():
    df = _df({"A": {"t1": 1.0}, "B": {"t1": 2.0, "t2": 3.0}})
    assert np.isnan(df.loc["A", "t2"])


def test_pairwise_complete_matches_manual_pearson():
    rows = {
        "A": {"t1": 1.0, "t2": 3.0, "t3": 7.0, "t4": 15.0, "t5": 4.0},
        "B": {"t1": 2.0, "t2": 5.0, "t3": 9.0, "t5": 3.0},  # missing t4
    }
    corr = analysis.compute_coexpression(_df(rows), min_obs=3)
    shared = ["t1", "t2", "t3", "t5"]
    a = np.log2(np.array([rows["A"][t] for t in shared]) + 1)
    b = np.log2(np.array([rows["B"][t] for t in shared]) + 1)
    assert corr.loc["A", "B"] == pytest.approx(np.corrcoef(a, b)[0, 1])
    assert corr.loc["A", "B"] == corr.loc["B", "A"]


def test_zero_fill_would_have_given_different_answer():
    # B is a perfect linear function of A on the shared tissues; B is unobserved
    # in t4/t5 where A is high. Zero-filling B there destroys the correlation.
    rows = {
        "A": {"t1": 1.0, "t2": 3.0, "t3": 7.0, "t4": 63.0, "t5": 127.0},
        "B": {"t1": 3.0, "t2": 7.0, "t3": 15.0},
    }
    corr = analysis.compute_coexpression(_df(rows), min_obs=3)
    assert corr.loc["A", "B"] == pytest.approx(1.0)

    zero_filled = _df(rows).fillna(0.0)
    old = np.log2(zero_filled + 1).T.corr().loc["A", "B"]
    assert old < 0.9  # what the previous implementation reported


def test_min_observation_gating_gives_nan_not_zero():
    rows = {"A": {"t1": 1.0, "t2": 2.0, "t3": 4.0, "t4": 8.0},
            "B": {"t1": 1.0, "t2": 2.0},  # only 2 shared tissues
            "C": {"t1": 2.0, "t2": 3.0, "t3": 5.0, "t4": 9.0}}
    corr = analysis.compute_coexpression(_df(rows), min_obs=3)
    assert np.isnan(corr.loc["A", "B"])
    assert not np.isnan(corr.loc["A", "C"])
    assert corr.loc["A", "C"] == pytest.approx(1.0, abs=0.01)
    # lowering the minimum makes the pair evaluable again
    assert not np.isnan(analysis.compute_coexpression(_df(rows), min_obs=2).loc["A", "B"])


def test_gated_pairs_excluded_from_score_and_top_pairs():
    rows = {"A": {"t1": 1.0, "t2": 2.0, "t3": 4.0, "t4": 8.0},
            "B": {"t1": 1.0},
            "C": {"t1": 8.0, "t2": 4.0, "t3": 2.0, "t4": 1.0}}
    r = analysis.run_full_analysis(rows)
    assert r["pathway_consistency_score"] == pytest.approx(-1.0, abs=0.05)  # only A-C counts
    assert [(p["gene_a"], p["gene_b"]) for p in r["top_correlated_pairs"]] == [("A", "C")]
    cov = r["coverage"]
    assert cov["pairs_total"] == 3 and cov["pairs_evaluated"] == 1
    assert cov["genes_dropped_low_coverage"] == ["B"]
    assert cov["gene_coverage"]["B"] == {"n_observed": 1, "n_tissues": 4, "low_coverage": True}
    assert cov["tissue_coverage"]["t4"] == {"n_observed": 2, "n_genes": 3}
    assert r["correlation_matrix"]["A"]["B"] is None
    assert r["summary_stats"]["B"]["n_observed"] == 1
    _dumps(r)


def test_pca_uses_only_complete_tissues():
    rows = {"A": {"t1": 1.0, "t2": 2.0, "t3": 4.0, "t4": 8.0},
            "B": {"t1": 2.0, "t2": 1.0, "t3": 9.0},
            "C": {"t1": 5.0, "t2": 3.0, "t3": 1.0, "t4": 2.0}}
    cov = analysis.run_full_analysis(rows)["coverage"]
    assert cov["pca_tissues_dropped"] == ["t4"]
    assert cov["pca_tissues_used"] == 3


def test_no_evaluable_pair_gives_none_score_and_router_style_guard():
    rows = {"A": {"t1": 1.0, "t2": 2.0, "t3": 3.0}, "B": {"t4": 1.0, "t5": 2.0, "t6": 3.0}}
    r = analysis.run_full_analysis(rows)
    assert r["pathway_consistency_score"] is None
    _dumps(r)


def test_gtex_missing_median_is_not_zero():
    import asyncio
    from unittest.mock import AsyncMock, patch
    from app.services import gtex

    recs = [
        {"gencodeId": "G1.1", "tissueSiteDetailId": "t1", "median": 5.0},
        {"gencodeId": "G1.1", "tissueSiteDetailId": "t2", "median": None},
        {"gencodeId": "G1.1", "tissueSiteDetailId": "t3"},
    ]
    with patch.object(gtex, "resolve_genes", AsyncMock(return_value={"A": "G1.1"})), \
         patch.object(gtex, "fetch_median_expression", AsyncMock(return_value=recs)):
        matrix, found, _ = asyncio.run(gtex.get_expression_matrix(["A"], "gtex_v8"))
    assert matrix == {"A": {"t1": 5.0}}
