#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUTPUT_PDF="${1:-docs/paper.pdf}"
OUTPUT_ABS="$ROOT_DIR/$OUTPUT_PDF"
WORK_DIR="$ROOT_DIR/v2/build"

mkdir -p "$(dirname "$OUTPUT_ABS")"

run_or_show_log() {
  local log_file="$1"
  shift
  if ! "$@" >"$log_file" 2>&1; then
    echo "Command failed: $*" >&2
    echo "Last 200 lines from $log_file:" >&2
    tail -n 200 "$log_file" >&2 || true
    return 1
  fi
}

(
  cd "$WORK_DIR"

  TEX_FILE="main.tex"
  BASENAME="main"
  TEMP_FINAL=0

  # Build a non-draft PDF for website downloads without changing source files.
  if grep -q '^\\documentclass\[runningheads, draft\]{llncs}' main.tex; then
    sed 's/^\\documentclass\[runningheads, draft\]{llncs}/\\documentclass[runningheads]{llncs}/' main.tex > main.ci-final.tex
    TEX_FILE="main.ci-final.tex"
    BASENAME="main.ci-final"
    TEMP_FINAL=1
  fi

  run_or_show_log "${BASENAME}.pdflatex.1.log" pdflatex -interaction=nonstopmode -halt-on-error "$TEX_FILE"
  run_or_show_log "${BASENAME}.bibtex.log" bibtex "$BASENAME"
  run_or_show_log "${BASENAME}.pdflatex.2.log" pdflatex -interaction=nonstopmode -halt-on-error "$TEX_FILE"
  run_or_show_log "${BASENAME}.pdflatex.3.log" pdflatex -interaction=nonstopmode -halt-on-error "$TEX_FILE"

  cp "${BASENAME}.pdf" "$OUTPUT_ABS"

  if [[ "$TEMP_FINAL" -eq 1 ]]; then
    rm -f \
      "${BASENAME}.tex" \
      "${BASENAME}.aux" \
      "${BASENAME}.bbl" \
      "${BASENAME}.blg" \
      "${BASENAME}.log" \
      "${BASENAME}.out" \
      "${BASENAME}.pdf" \
      "${BASENAME}.toc" \
      "${BASENAME}.xref" \
      "${BASENAME}.dvi" \
      "${BASENAME}.4ct" \
      "${BASENAME}.4tc" \
      "${BASENAME}.idv" \
      "${BASENAME}.lg" \
      "${BASENAME}.tmp" \
      "${BASENAME}.bibtex.log" \
      "${BASENAME}.pdflatex.1.log" \
      "${BASENAME}.pdflatex.2.log" \
      "${BASENAME}.pdflatex.3.log"
  fi
)

test -s "$OUTPUT_ABS"
