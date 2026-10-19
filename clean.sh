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

PYCACHE_DIRS=()
while IFS= read -r -d '' p; do PYCACHE_DIRS+=("$p"); done < <(find backend -type d -name "__pycache__" -print0 2>/dev/null)
PYCS=()
while IFS= read -r -d '' p; do PYCS+=("$p"); done < <(find backend -name "*.pyc" -print0 2>/dev/null)

KB_venv=$(kb_of backend/.venv)
KB_node=$(kb_of frontend/node_modules)
KB_dist=$(kb_of frontend/dist)
KB_pytest=$(kb_of backend/.pytest_cache backend/htmlcov backend/.coverage)
KB_pyc=$(kb_of "${PYCACHE_DIRS[@]}" "${PYCS[@]}")
KB_cache=$(kb_of backend/app/data/gtex_gene_cache.json)

total_kb=$(( KB_venv + KB_node + KB_dist + KB_pytest + KB_pyc + KB_cache ))

if ! $FORCE; then
  echo "Dry run — would remove:"
  printf "  %-50s %s\n" "backend/.venv"                                "$(kb_hr $KB_venv)"
  printf "  %-50s %s\n" "frontend/node_modules"                        "$(kb_hr $KB_node)"
  printf "  %-50s %s\n" "frontend/dist"                                "$(kb_hr $KB_dist)"
  printf "  %-50s %s\n" "backend/.pytest_cache, htmlcov, .coverage"    "$(kb_hr $KB_pytest)"
  printf "  %-50s %s\n" "backend/**/__pycache__ (and *.pyc)"           "$(kb_hr $KB_pyc)"
  printf "  %-50s %s\n" "backend/app/data/gtex_gene_cache.json (restore from git)" "$(kb_hr $KB_cache)"
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

# The cache is a git-tracked, shipped data file: restore it rather than wiping it.
# (Only newly resolved, untracked write-backs are lost.)
git checkout -- backend/app/data/gtex_gene_cache.json 2>/dev/null \
  || echo "Note: could not restore gtex_gene_cache.json from git; left unchanged."

echo "Done."
echo ""
echo "To start fresh: ./start.sh"
