"""Gene cache: puts are in-memory, flush is batched and atomic."""

import json
from unittest.mock import patch

import app.services.gene_cache as gc

_REAL_FLUSH = gc._flush  # conftest patches gc._flush for every test


def _fresh(tmp_path):
    return patch.multiple(gc, _cache={}, _loaded=True, _dirty=False, _flush=_REAL_FLUSH)


def test_put_does_not_write_and_flush_writes_once(tmp_path):
    path = tmp_path / "cache.json"
    with _fresh(tmp_path), patch("app.services.gene_cache._flush", wraps=_REAL_FLUSH) as fl:  # real impl, counted
        for i in range(50):
            gc.put(f"G{i}", f"ENSG{i}.1")
        assert not path.exists()
        assert fl.call_count == 0
        gc.flush(path)
        gc.flush(path)  # second flush is a no-op: nothing dirty
        assert fl.call_count == 1
    data = json.loads(path.read_text())
    assert len(data) == 50 and data["G7"] == "ENSG7.1"


def test_flush_is_atomic_and_leaves_no_temp_files(tmp_path):
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({"_meta": {"v": 1}, "OLD": "ENSG0.1"}))
    with _fresh(tmp_path):
        gc.put("NEW", "ENSG9.1")
        # simulate a crash during the write: the original file must stay intact
        with patch("app.services.gene_cache.os.replace", side_effect=OSError("boom")):
            gc.flush(path)
    assert json.loads(path.read_text()) == {"_meta": {"v": 1}, "OLD": "ENSG0.1"}
    assert [p.name for p in tmp_path.iterdir()] == ["cache.json"]


def test_flush_preserves_meta(tmp_path):
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({"_meta": {"v": 1}}))
    with _fresh(tmp_path):
        gc.put("A", "ENSG1.1")
        gc.flush(path)
    assert json.loads(path.read_text())["_meta"] == {"v": 1}
