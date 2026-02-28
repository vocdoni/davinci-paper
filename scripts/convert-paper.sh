#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUTPUT_DIR="${1:-docs/md}"
mkdir -p "$OUTPUT_DIR"

./scripts/prepare-flattened-tex.sh

FLAT_TEX="$ROOT_DIR/build/flat/flattened.tex"
RESOURCE_PATH="$ROOT_DIR/build/flat:$ROOT_DIR/build/flat/texsrc/build:$ROOT_DIR/build/flat/texsrc/sections:$ROOT_DIR/build/flat/texsrc/figures:$ROOT_DIR/v2/build:$ROOT_DIR/v2/sections:$ROOT_DIR/v2/figures:$ROOT_DIR/v2/bibliography"

(
  cd "$OUTPUT_DIR"
  pandoc "$FLAT_TEX" \
    --from=latex+raw_tex \
    --to=gfm+tex_math_dollars \
    --wrap=none \
    --markdown-headings=atx \
    --resource-path="$RESOURCE_PATH" \
    --citeproc \
    --bibliography="$ROOT_DIR/v2/bibliography/bibtex.bib" \
    --extract-media=media \
    --strip-comments \
    -o paper.md
)

# Clean residual LaTeX wrappers that are not useful in markdown output.
perl -0777 -i -pe '
  s/\\hyperlink\{[^{}]*\}\{([^{}]*)\}/$1/g;
  s/\\hypertarget\{[^{}]*\}\{([^{}]*)\}/$1/g;
  s/\\ensuremath\{/\{/g;
  s/\\ensuremath\{([^{}]+)\}/$1/g;
  s/\\detokenize\{([^{}]+)\}/$1/g;
  s/\{\\sf\{([^{}]+)\}\}/\\texttt{$1}/g;
  s/\\sf\{([^{}]+)\}/\\texttt{$1}/g;
  s/\{\\tt\{([^{}]+)\}\}/\\texttt{$1}/g;
  s/\\tt\{([^{}]+)\}/\\texttt{$1}/g;
  s/\\text\{\\tiny\s*\\sf\s*([^{}]+)\}/\\mathrm{$1}/g;
  s/\\text\{\\tiny\s*\\mathsf\{([^{}]+)\}\}/\\mathrm{$1}/g;
  s/\\xspace//g;
  s/\\hspace\{[^}]*\}//g;
  s/\\rule\{[^}]*\}\{[^}]*\}//g;
  s/\\allowbreak//g;
  s/\$\$\\label\{[^}]+\}\s*/\$\$/g;
  s/\\:\|\|\\:/ || /g;
  s/\[\]\(#\\detokenize\{([^}]*)\}\)/$1/g;
' "$OUTPUT_DIR/paper.md"

# Ensure media links remain relative for /md hosting.
perl -0777 -i -pe '
  s#(?:\.\./)*docs/(?:md/)?media/#media/#g;
' "$OUTPUT_DIR/paper.md"

./scripts/postprocess-web-output.sh "$OUTPUT_DIR" "$OUTPUT_DIR/paper.md"

test -s "$OUTPUT_DIR/paper.md"
