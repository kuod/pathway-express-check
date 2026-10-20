"""Report endpoint tests (small synthetic payload)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.reports import _safe_filename

client = TestClient(app)


def _payload(name="HALLMARK_X"):
    return {
        "pathway_name": name,
        "pathway_genes": ["A", "B"],
        "expression": {
            "genes_found": ["A", "B"],
            "genes_not_found": [],
            "tissues": ["t1", "t2", "t3"],
            "expression_matrix": {
                "A": {"t1": 1.0, "t2": 5.0, "t3": 9.0},
                "B": {"t1": 2.0, "t2": 6.0, "t3": 10.0},
            },
        },
        "coexpression": {
            "correlation_matrix": {"A": {"A": 1.0, "B": 1.0}, "B": {"A": 1.0, "B": 1.0}},
            "pathway_consistency_score": 1.0,
            "top_correlated_pairs": [{"gene_a": "A", "gene_b": "B", "pearson_r": 1.0}],
            "summary_stats": {"A": {"mean_tpm": 5.0}, "B": {"mean_tpm": 6.0}},
            "pca_variance_explained": [1.0, 0.0],
            "pca_coordinates": {"A": [1.0, 0.0], "B": [-1.0, 0.0]},
        },
    }


@pytest.mark.parametrize(
    "raw",
    ['a"b', "x\r\nSet-Cookie: y", "café – pathway", "../../etc/passwd", ""],
)
def test_safe_filename_has_no_header_hazards(raw):
    out = _safe_filename(raw, ".docx")
    assert out.endswith(".docx")
    assert all(c.isalnum() or c in "._-" for c in out)
    assert ".." not in out.replace("._", "")  # no traversal sequences


@pytest.mark.parametrize("path,ext", [("docx", ".docx"), ("data/csv", ".xlsx")])
def test_download_with_hostile_name(path, ext):
    r = client.post(f"/api/reports/{path}", json=_payload('a"b\r\nX: y é'))
    assert r.status_code == 200
    disp = r.headers["content-disposition"]
    assert "\r" not in disp and "\n" not in disp
    assert disp.endswith(ext + '"')


def test_html_report_escapes_pathway_name():
    r = client.post("/api/reports/html", json=_payload("<script>alert(1)</script>"))
    assert r.status_code == 200
    assert "<script>alert(1)</script>" not in r.text


def test_figures_zip():
    r = client.post("/api/reports/figures/zip", json=_payload())
    assert r.status_code == 200
    assert r.content[:2] == b"PK"


def test_figure_helpers_threadsafe_and_leave_no_pyplot_figures():
    from concurrent.futures import ThreadPoolExecutor
    import matplotlib.pyplot as plt
    from app.routers.reports import _correlation_heatmap_png, _expression_heatmap_png

    p = _payload()
    expr = p["expression"]["expression_matrix"]
    corr = p["coexpression"]["correlation_matrix"]
    with ThreadPoolExecutor(8) as ex:
        futs = [ex.submit(_expression_heatmap_png if i % 2 else _correlation_heatmap_png,
                          expr if i % 2 else corr) for i in range(16)]
        outs = [f.result() for f in futs]
    assert all(o.startswith(b"\x89PNG") for o in outs)
    assert plt.get_fignums() == []


@pytest.mark.parametrize("info", ["GTEx v8", "GTEx v10"])
def test_html_report_methods_do_not_hardcode_gencode_version(info):
    body = _payload()
    body["dataset_info"] = info
    body["include_methods"] = True
    r = client.post("/api/reports/html", json=body)
    assert r.status_code == 200
    assert info in r.text
    assert "GENCODE v26" not in r.text
