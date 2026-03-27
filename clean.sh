#!/usr/bin/env bash
set -e

echo "Cleaning pathway-express-check artifacts..."

# Python virtual environment
rm -rf backend/.venv

# Python bytecode
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find backend -name "*.pyc" -delete 2>/dev/null || true

# Pytest / coverage
rm -rf backend/.pytest_cache backend/htmlcov backend/.coverage

# Frontend dependencies and build output
rm -rf frontend/node_modules frontend/dist

# GTEx gene cache (reset to empty object; file is git-tracked)
echo "{}" > backend/app/data/gtex_gene_cache.json

echo "Done."
echo ""
echo "To start fresh: ./start.sh"
