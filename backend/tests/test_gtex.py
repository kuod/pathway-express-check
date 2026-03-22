"""
Unit tests for app/services/gtex.py.

All HTTP calls are intercepted with unittest.mock so no network access is needed.
Run with:  pytest tests/test_gtex.py -v
"""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch, call

import app.services.gtex as gtex
import app.services.gene_cache as gc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    """Return a mock httpx.Response that returns *payload* as JSON."""
    r = MagicMock(spec=httpx.Response)
    r.status_code = status_code
    r.json.return_value = payload
    if status_code >= 400:
        r.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=r
        )
    else:
        r.raise_for_status.return_value = None
    return r


# ---------------------------------------------------------------------------
# resolve_genes
# ---------------------------------------------------------------------------

class TestResolveGenes:
    @pytest.mark.asyncio
    async def test_returns_gencode_id_from_data_key(self):
        """Parses gencodeId from response["data"][0]."""
        payload = {"data": [{"gencodeId": "ENSG00000141510.16", "geneSymbol": "TP53"}]}
        mock_get = AsyncMock(return_value=_mock_response(payload))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            result = await gtex.resolve_genes(["TP53"])

        assert result == {"TP53": "ENSG00000141510.16"}

    @pytest.mark.asyncio
    async def test_uses_correct_genome_build_param(self):
        """Sends genomeBuild=GRCh38/hg38, not GRCh38 (which causes a 422)."""
        payload = {"data": [{"gencodeId": "ENSG00000141510.16"}]}
        mock_get = AsyncMock(return_value=_mock_response(payload))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            await gtex.resolve_genes(["TP53"])

        _, kwargs = mock_get.call_args
        assert kwargs["params"]["genomeBuild"] == "GRCh38/hg38", (
            "genomeBuild must be 'GRCh38/hg38'; 'GRCh38' alone returns 422"
        )

    @pytest.mark.asyncio
    async def test_unknown_symbol_returns_none(self):
        """Empty data list → symbol maps to None (not KeyError)."""
        payload = {"data": []}
        mock_get = AsyncMock(return_value=_mock_response(payload))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            result = await gtex.resolve_genes(["NOTAREAL"])

        assert result == {"NOTAREAL": None}

    @pytest.mark.asyncio
    async def test_http_error_maps_symbol_to_none(self):
        """Network / 4xx errors are swallowed; symbol maps to None."""
        mock_get = AsyncMock(side_effect=httpx.RequestError("timeout"))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            result = await gtex.resolve_genes(["TP53"])

        assert result == {"TP53": None}

    @pytest.mark.asyncio
    async def test_old_gene_key_would_fail(self):
        """
        Regression guard: if code had used data.get("gene", []) it would return
        None even with a valid response.  Confirm "data" key is honoured.
        """
        # Simulate a response that has "gene" but NOT "data" (old wrong shape)
        payload = {"gene": [{"gencodeId": "ENSG00000141510.16"}]}
        mock_get = AsyncMock(return_value=_mock_response(payload))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            result = await gtex.resolve_genes(["TP53"])

        # Code should now look for "data", so this mis-shaped payload → None
        assert result == {"TP53": None}

    @pytest.mark.asyncio
    async def test_multiple_symbols_resolved_independently(self):
        payloads = {
            "TP53":  {"data": [{"gencodeId": "ENSG00000141510.16"}]},
            "BRCA1": {"data": [{"gencodeId": "ENSG00000012048.21"}]},
            "FAKE":  {"data": []},
        }

        async def fake_get(url, *, params, timeout):
            symbol = params["geneId"]
            return _mock_response(payloads[symbol])

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = fake_get
            result = await gtex.resolve_genes(["TP53", "BRCA1", "FAKE"])

        assert result["TP53"] == "ENSG00000141510.16"
        assert result["BRCA1"] == "ENSG00000012048.21"
        assert result["FAKE"] is None


# ---------------------------------------------------------------------------
# resolve_genes — cache behaviour
# ---------------------------------------------------------------------------

class TestResolveGenesCache:
    @pytest.mark.asyncio
    async def test_cache_hit_skips_http(self):
        """A symbol already in cache must not trigger any HTTP request."""
        with patch("app.services.gene_cache._cache", {"TP53": "ENSG00000141510.16"}), \
             patch("app.services.gene_cache._loaded", True):
            with patch("httpx.AsyncClient") as MockClient:
                result = await gtex.resolve_genes(["TP53"])
                MockClient.assert_not_called()

        assert result == {"TP53": "ENSG00000141510.16"}

    @pytest.mark.asyncio
    async def test_cache_miss_writes_back(self):
        """A symbol resolved via API must be stored in cache (write-back)."""
        payload = {"data": [{"gencodeId": "ENSG00000141510.16", "geneSymbol": "TP53"}]}
        mock_get = AsyncMock(return_value=_mock_response(payload))

        shared_cache: dict = {}
        with patch("app.services.gene_cache._cache", shared_cache), \
             patch("app.services.gene_cache._loaded", True), \
             patch("app.services.gene_cache._flush"):  # avoid actual file I/O
            with patch("httpx.AsyncClient") as MockClient:
                MockClient.return_value.__aenter__.return_value.get = mock_get
                result = await gtex.resolve_genes(["TP53"])

        assert result["TP53"] == "ENSG00000141510.16"
        assert shared_cache.get("TP53") == "ENSG00000141510.16"

    @pytest.mark.asyncio
    async def test_partial_cache_hit_only_fetches_uncached(self):
        """Only the symbol not in cache should produce an HTTP request."""
        brca1_payload = {"data": [{"gencodeId": "ENSG00000012048.21", "geneSymbol": "BRCA1"}]}
        mock_get = AsyncMock(return_value=_mock_response(brca1_payload))

        shared_cache = {"TP53": "ENSG00000141510.16"}
        with patch("app.services.gene_cache._cache", shared_cache), \
             patch("app.services.gene_cache._loaded", True), \
             patch("app.services.gene_cache._flush"):
            with patch("httpx.AsyncClient") as MockClient:
                MockClient.return_value.__aenter__.return_value.get = mock_get
                result = await gtex.resolve_genes(["TP53", "BRCA1"])

        assert result["TP53"] == "ENSG00000141510.16"
        assert result["BRCA1"] == "ENSG00000012048.21"
        assert mock_get.call_count == 1, "Only BRCA1 should hit the API; TP53 was cached"


# ---------------------------------------------------------------------------
# fetch_median_expression
# ---------------------------------------------------------------------------

class TestFetchMedianExpression:
    @pytest.mark.asyncio
    async def test_parses_data_key(self):
        """Records come from response["data"], not "medianGeneExpression"."""
        record = {
            "gencodeId": "ENSG00000141510.16",
            "geneSymbol": "TP53",
            "tissueSiteDetailId": "Liver",
            "median": 3.14,
            "unit": "TPM",
        }
        payload = {"data": [record]}
        mock_get = AsyncMock(return_value=_mock_response(payload))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            result = await gtex.fetch_median_expression(["ENSG00000141510.16"])

        assert result == [record]

    @pytest.mark.asyncio
    async def test_old_medianGeneExpression_key_returns_empty(self):
        """
        Regression guard: old key "medianGeneExpression" is ignored.
        If the code still used that key, this would incorrectly return data.
        """
        record = {"gencodeId": "ENSG00000141510.16", "tissueSiteDetailId": "Liver", "median": 1.0}
        payload = {"medianGeneExpression": [record]}  # wrong key
        mock_get = AsyncMock(return_value=_mock_response(payload))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            result = await gtex.fetch_median_expression(["ENSG00000141510.16"])

        assert result == [], "Code must read 'data' key; old 'medianGeneExpression' key should yield empty"

    @pytest.mark.asyncio
    async def test_gencodeId_param_is_list(self):
        """
        gencodeId must be passed as a list so httpx serialises it as repeated
        params (?gencodeId=ID1&gencodeId=ID2).  A comma-joined string produces
        a single encoded value that the GTEx API ignores, returning empty data.
        """
        mock_get = AsyncMock(return_value=_mock_response({"data": []}))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            await gtex.fetch_median_expression(
                ["ENSG00000141510.16", "ENSG00000012048.21"]
            )

        _, kwargs = mock_get.call_args
        gencode_param = kwargs["params"]["gencodeId"]

        assert isinstance(gencode_param, list), (
            "gencodeId must be a list so httpx repeats the key; "
            "a comma-joined string causes GTEx to return empty data"
        )
        assert gencode_param == ["ENSG00000141510.16", "ENSG00000012048.21"]

    @pytest.mark.asyncio
    async def test_batches_large_gene_lists(self):
        """Gene lists longer than _GENE_BATCH_SIZE are split across multiple requests."""
        ids = [f"ENSG{i:011d}.1" for i in range(25)]  # 25 genes → 2 batches
        mock_get = AsyncMock(return_value=_mock_response({"data": []}))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            await gtex.fetch_median_expression(ids)

        assert mock_get.call_count == 2, "25 genes / batch-size-20 should produce 2 requests"

    @pytest.mark.asyncio
    async def test_batch_failure_is_non_fatal(self):
        """A single failing batch doesn't raise; other batches still contribute."""
        ids = [f"ENSG{i:011d}.1" for i in range(25)]
        good_record = {"gencodeId": ids[0], "tissueSiteDetailId": "Liver", "median": 1.0}

        call_count = 0

        async def sometimes_fail(url, *, params, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.RequestError("simulated timeout")
            return _mock_response({"data": [good_record]})

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = sometimes_fail
            result = await gtex.fetch_median_expression(ids)

        assert result == [good_record]

    @pytest.mark.asyncio
    async def test_combines_records_across_batches(self):
        """Records from all batches are merged into a single list."""
        ids = [f"ENSG{i:011d}.1" for i in range(45)]  # 3 batches (20+20+5)
        batch_record = lambda i: {"gencodeId": ids[i], "tissueSiteDetailId": "Liver", "median": float(i)}

        batch_num = 0

        async def per_batch(url, *, params, timeout):
            nonlocal batch_num
            r = batch_record(batch_num * gtex._GENE_BATCH_SIZE)
            batch_num += 1
            return _mock_response({"data": [r]})

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = per_batch
            result = await gtex.fetch_median_expression(ids)

        assert len(result) == 3


# ---------------------------------------------------------------------------
# list_tissues
# ---------------------------------------------------------------------------

class TestListTissues:
    @pytest.mark.asyncio
    async def test_uses_correct_endpoint(self):
        """Calls /dataset/tissueSiteDetail, not the old /dataset/tissueInfo."""
        mock_get = AsyncMock(return_value=_mock_response({"data": []}))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            await gtex.list_tissues()

        url_called = mock_get.call_args[0][0]
        assert url_called.endswith("/dataset/tissueSiteDetail"), (
            f"Wrong endpoint: {url_called}. Should be /dataset/tissueSiteDetail"
        )
        assert not url_called.endswith("/dataset/tissueInfo"), "Old endpoint /dataset/tissueInfo returns 404"

    @pytest.mark.asyncio
    async def test_parses_data_key(self):
        tissue = {"tissueSiteDetailId": "Liver", "tissueSiteDetail": "Liver", "colorHex": "AABB00"}
        mock_get = AsyncMock(return_value=_mock_response({"data": [tissue]}))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            result = await gtex.list_tissues()

        assert result == [tissue]

    @pytest.mark.asyncio
    async def test_old_tissueInfo_key_returns_empty(self):
        """Regression guard: old key 'tissueInfo' is no longer used."""
        tissue = {"tissueSiteDetailId": "Liver"}
        mock_get = AsyncMock(return_value=_mock_response({"tissueInfo": [tissue]}))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            result = await gtex.list_tissues()

        assert result == []

    @pytest.mark.asyncio
    async def test_no_datasetId_param_sent(self):
        """tissueSiteDetail endpoint doesn't need/use datasetId."""
        mock_get = AsyncMock(return_value=_mock_response({"data": []}))

        with patch("httpx.AsyncClient") as MockClient:
            MockClient.return_value.__aenter__.return_value.get = mock_get
            await gtex.list_tissues()

        call_kwargs = mock_get.call_args[1]
        assert "params" not in call_kwargs or "datasetId" not in (call_kwargs.get("params") or {}), (
            "datasetId param should not be sent to tissueSiteDetail"
        )


# ---------------------------------------------------------------------------
# get_expression_matrix  (integration of the above)
# ---------------------------------------------------------------------------

class TestGetExpressionMatrix:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_genes_resolve(self):
        with patch.object(gtex, "resolve_genes", return_value={"FAKE": None}):
            matrix, found, not_found = await gtex.get_expression_matrix(["FAKE"])

        assert matrix == {}
        assert found == []
        assert "FAKE" in not_found

    @pytest.mark.asyncio
    async def test_full_flow_builds_matrix(self):
        id_map = {"TP53": "ENSG00000141510.16"}
        records = [
            {"gencodeId": "ENSG00000141510.16", "tissueSiteDetailId": "Liver", "median": 5.0},
            {"gencodeId": "ENSG00000141510.16", "tissueSiteDetailId": "Brain", "median": 2.0},
        ]
        with patch.object(gtex, "resolve_genes", return_value=id_map), \
             patch.object(gtex, "fetch_median_expression", return_value=records):
            matrix, found, not_found = await gtex.get_expression_matrix(["TP53"])

        assert "TP53" in matrix
        assert matrix["TP53"]["Liver"] == 5.0
        assert matrix["TP53"]["Brain"] == 2.0
        assert found == ["TP53"]
        assert not_found == []

    @pytest.mark.asyncio
    async def test_version_suffix_mismatch_falls_back_to_base_id(self):
        """
        GTEx sometimes returns a different version suffix than what was resolved.
        e.g. resolved ENSG00000141510.16 but expression record has ENSG00000141510.17.
        The base-ID fallback should still match the symbol.
        """
        id_map = {"TP53": "ENSG00000141510.16"}
        records = [
            # Different version (.17 vs .16)
            {"gencodeId": "ENSG00000141510.17", "tissueSiteDetailId": "Liver", "median": 3.0},
        ]
        with patch.object(gtex, "resolve_genes", return_value=id_map), \
             patch.object(gtex, "fetch_median_expression", return_value=records):
            matrix, found, not_found = await gtex.get_expression_matrix(["TP53"])

        assert "TP53" in matrix, "Base-ID fallback should match despite version suffix difference"
        assert matrix["TP53"]["Liver"] == 3.0

    @pytest.mark.asyncio
    async def test_genes_with_no_expression_records_go_to_not_found(self):
        """Resolved genes that return no expression rows are reported as not found."""
        id_map = {"TP53": "ENSG00000141510.16", "BRCA1": "ENSG00000012048.21"}
        records = [
            {"gencodeId": "ENSG00000141510.16", "tissueSiteDetailId": "Liver", "median": 5.0},
            # No records for BRCA1
        ]
        with patch.object(gtex, "resolve_genes", return_value=id_map), \
             patch.object(gtex, "fetch_median_expression", return_value=records):
            matrix, found, not_found = await gtex.get_expression_matrix(["TP53", "BRCA1"])

        assert "TP53" in matrix
        assert "BRCA1" not in matrix
        assert "BRCA1" in not_found
