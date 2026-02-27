#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p build/flat docs

TMP_TEX_ROOT="build/flat/texsrc"
rm -rf "$TMP_TEX_ROOT"
cp -R v2 "$TMP_TEX_ROOT"

# latexpand does not resolve macro-based include prefixes like \secs/, so
# normalize them to explicit relative paths in a temporary conversion tree.
while IFS= read -r -d '' tex_file; do
  sed -E \
    -e 's#\\input\{\\secs/#\\input{../sections/#g' \
    -e 's#\\input\{\\figs/#\\input{../figures/#g' \
    -e 's#\\includegraphics(\[[^]]*\])?\{\\figs/#\\includegraphics\1{../figures/#g' \
    -e 's#\\bibliography\{\\bib/#\\bibliography{../bibliography/#g' \
    "$tex_file" > "${tex_file}.tmp"
  mv "${tex_file}.tmp" "$tex_file"
done < <(find "$TMP_TEX_ROOT" -type f -name '*.tex' -print0)

# Support extensionless \includegraphics{...} paths by adding symlink aliases.
if [[ -d "$TMP_TEX_ROOT/figures" ]]; then
  while IFS= read -r -d '' figure_file; do
    figure_base="${figure_file%.*}"
    if [[ "$figure_file" != "$figure_base" && ! -e "$figure_base" ]]; then
      ln -s "$(basename "$figure_file")" "$figure_base"
    fi
  done < <(find "$TMP_TEX_ROOT/figures" -maxdepth 1 -type f -print0)
fi

(
  cd "$TMP_TEX_ROOT/build"
  latexpand main.tex > "$ROOT_DIR/build/flat/flattened.tex"
)

pandoc build/flat/flattened.tex \
  --from=latex+raw_tex \
  --to=gfm+tex_math_dollars \
  --wrap=none \
  --markdown-headings=atx \
  --resource-path=build/flat:build/flat/texsrc/build:build/flat/texsrc/sections:build/flat/texsrc/figures:v2/build:v2/sections:v2/figures:v2/bibliography \
  --citeproc \
  --bibliography=v2/bibliography/bibtex.bib \
  --extract-media=docs/media \
  --strip-comments \
  -o docs/paper.md

test -s docs/paper.md
