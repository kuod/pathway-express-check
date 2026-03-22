"""
Shared pytest fixtures for the backend test suite.
"""

import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def empty_gene_cache():
    """Reset gene cache state for every test to prevent cross-test pollution and disk I/O."""
    with patch("app.services.gene_cache._cache", {}), \
         patch("app.services.gene_cache._loaded", True), \
         patch("app.services.gene_cache._flush"):
        yield
