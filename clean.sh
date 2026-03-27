#!/usr/bin/env bash
set -e

FORCE=false
if [[ "${1}" == "--force" ]]; then
  FORCE=true
fi

# Items to clean: "description|command"
TARGETS=(
  "backend/.venv"
  "frontend/node_modules"
  "frontend/dist"
  "backend/.pytest_cache"
  "backend/htmlcov"
  "backend/.coverage"
  "backend/**/__pycache__ (and *.pyc)"
  "backend/app/data/gtex_gene_cache.json → reset to {}"
)

if ! $FORCE; then
  echo "Dry run — would remove:"
  for t in "${TARGETS[@]}"; do
    echo "  $t"
  done
  echo ""
  echo "Run './clean.sh --force' to execute."
  exit 0
fi

echo "Cleaning pathway-express-check artifacts..."

rm -rf backend/.venv

find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find backend -name "*.pyc" -delete 2>/dev/null || true

rm -rf backend/.pytest_cache backend/htmlcov backend/.coverage

rm -rf frontend/node_modules frontend/dist

echo "{}" > backend/app/data/gtex_gene_cache.json

echo "Done."
echo ""
echo "To start fresh: ./start.sh"
