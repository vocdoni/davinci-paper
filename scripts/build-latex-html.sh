#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUTPUT_DIR="${1:-docs}"
MD_PATH="${2:-./md/}"
mkdir -p "$OUTPUT_DIR"

./scripts/prepare-flattened-tex.sh

FLAT_TEX="$ROOT_DIR/build/flat/flattened.tex"
RESOURCE_PATH="$ROOT_DIR/build/flat:$ROOT_DIR/build/flat/texsrc/build:$ROOT_DIR/build/flat/texsrc/sections:$ROOT_DIR/build/flat/texsrc/figures:$ROOT_DIR/v2/build:$ROOT_DIR/v2/sections:$ROOT_DIR/v2/figures:$ROOT_DIR/v2/bibliography"

(
  cd "$OUTPUT_DIR"
  pandoc "$FLAT_TEX" \
    --from=latex+raw_tex \
    --to=html5 \
    --standalone \
    --mathjax=https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js \
    --resource-path="$RESOURCE_PATH" \
    --citeproc \
    --bibliography="$ROOT_DIR/v2/bibliography/bibtex.bib" \
    --extract-media=media \
    --metadata title="DaVinci Paper" \
    -o index.html
)

perl -0777 -i -pe "
  s~</head>~<style>
  :root { color-scheme: light; }
  body { margin: 0 auto; max-width: 980px; padding: 26px 18px 48px; color: #1f2328; line-height: 1.72; background: #f6f8fa; }
  .paper-nav { position: sticky; top: 0; z-index: 10; margin: -26px -18px 20px; padding: 10px 14px; border-bottom: 1px solid #d0d7de; background: rgba(255,255,255,0.95); backdrop-filter: blur(4px); }
  .paper-nav a { display: inline-block; margin-right: 8px; text-decoration: none; border: 1px solid #d0d7de; border-radius: 6px; padding: 6px 10px; color: #1f2328; background: #f6f8fa; font: 600 14px/1.2 -apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif; }
  p, li, td, th, blockquote { color: #1f2328; }
  h1, h2, h3, h4, h5, h6 { color: #0f172a; }
  img, embed, object { max-width: 100%; width: 100% !important; height: auto !important; display: block; margin: 0 auto; border-radius: 6px; }
  figure { margin: 1.2rem 0; max-width: 100%; }
  figure > img { width: 100% !important; }
  figcaption { color: #57606a; font-size: 0.95rem; }
  pre { overflow-x: auto; background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 8px; padding: 10px; }
  @media (max-width: 767px) { body { padding: 14px 12px 28px; } .paper-nav { margin: -14px -12px 16px; } }
  </style></head>~s;
  s~<body([^>]*)>~<body\\1><div class='paper-nav'><a href='paper.pdf' download>Download paper.pdf</a><a href='$MD_PATH'>Markdown View</a><a href='${MD_PATH}paper.md' download>Download paper.md</a></div>~s;
" "$OUTPUT_DIR/index.html"

# Ensure extracted media links are relative in deployed root page.
perl -0777 -i -pe '
  s#(?:\.\./)*docs/(?:md/)?media/#media/#g;
' "$OUTPUT_DIR/index.html"

./scripts/postprocess-web-output.sh "$OUTPUT_DIR" "$OUTPUT_DIR/index.html"

test -s "$OUTPUT_DIR/index.html"
