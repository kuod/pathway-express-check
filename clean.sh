#!/usr/bin/env bash
set -e

FORCE=false
if [[ "${1}" == "--force" ]]; then
  FORCE=true
fi

kb_of() {
  # Return total size in KB for all existing paths passed as args
  local total=0
  for p in "$@"; do
    [[ -e "$p" ]] && total=$(( total + $(du -sk "$p" 2>/dev/null | awk '{print $1}') ))
  done
  echo "$total"
}

kb_hr() {
  local kb=$1
  if (( kb >= 1048576 )); then
    printf "%.1f GB" "$(echo "scale=1; $kb/1048576" | bc)"
  elif (( kb >= 1024 )); then
    printf "%.1f MB" "$(echo "scale=1; $kb/1024" | bc)"
  else
    printf "%d KB" "$kb"
  fi
}

mapfile -d '' PYCACHE_DIRS < <(find backend -type d -name "__pycache__" -print0 2>/dev/null)
mapfile -d '' PYCS        < <(find backend -name "*.pyc" -print0 2>/dev/null)

declare -A ITEM_KB
ITEM_KB[venv]=$(kb_of backend/.venv)
ITEM_KB[node]=$(kb_of frontend/node_modules)
ITEM_KB[dist]=$(kb_of frontend/dist)
ITEM_KB[pytest]=$(kb_of backend/.pytest_cache backend/htmlcov backend/.coverage)
ITEM_KB[pyc]=$(kb_of "${PYCACHE_DIRS[@]}" "${PYCS[@]}")
ITEM_KB[cache]=$(kb_of backend/app/data/gtex_gene_cache.json)

total_kb=$(( ITEM_KB[venv] + ITEM_KB[node] + ITEM_KB[dist] + ITEM_KB[pytest] + ITEM_KB[pyc] + ITEM_KB[cache] ))

if ! $FORCE; then
  echo "Dry run — would remove:"
  printf "  %-50s %s\n" "backend/.venv"                                "$(kb_hr ${ITEM_KB[venv]})"
  printf "  %-50s %s\n" "frontend/node_modules"                        "$(kb_hr ${ITEM_KB[node]})"
  printf "  %-50s %s\n" "frontend/dist"                                "$(kb_hr ${ITEM_KB[dist]})"
  printf "  %-50s %s\n" "backend/.pytest_cache, htmlcov, .coverage"    "$(kb_hr ${ITEM_KB[pytest]})"
  printf "  %-50s %s\n" "backend/**/__pycache__ (and *.pyc)"           "$(kb_hr ${ITEM_KB[pyc]})"
  printf "  %-50s %s\n" "backend/app/data/gtex_gene_cache.json → {}"  "$(kb_hr ${ITEM_KB[cache]})"
  echo ""
  echo "Total storage reclaimed: $(kb_hr $total_kb)"
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
