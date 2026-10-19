from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_unknown_library_is_404_not_500():
    with patch("app.services.msigdb.list_libraries", return_value=["HALLMARK"]):
        assert client.get("/api/pathways/search", params={"library": "nope"}).status_code == 404
        assert client.get("/api/pathways/nope/X").status_code == 404


def test_max_results_must_be_positive():
    assert client.get("/api/pathways/search", params={"library": "L", "max_results": 0}).status_code == 422
    assert client.get("/api/pathways/search", params={"library": "L", "max_results": -1}).status_code == 422


def test_search_and_get_pathway():
    sets = {"A_ONE": ["G1", "G2"], "B_TWO": ["G3"]}
    with patch("app.services.msigdb.list_libraries", return_value=["L"]), \
         patch("app.services.msigdb.load_library", return_value=sets):
        r = client.get("/api/pathways/search", params={"library": "L", "query": "one"})
        assert r.json() == [{"name": "A_ONE", "gene_count": 2}]
        assert client.get("/api/pathways/L/A_ONE").json()["genes"] == ["G1", "G2"]
        assert client.get("/api/pathways/L/MISSING").status_code == 404
