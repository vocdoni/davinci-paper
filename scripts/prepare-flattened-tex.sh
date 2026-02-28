#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p build/flat

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

# Use conversion-friendly macro styles to avoid leaking complex LaTeX wrappers.
cat >> "$TMP_TEX_ROOT/build/preamble-macros.tex" <<'EOF'
\renewcommand{\hlset}[1]{#1}
\renewcommand{\hlget}[1]{#1}
\renewcommand{\circuitstyle}[1]{\texttt{#1}\xspace}
\renewcommand{\smartcontractstyle}[1]{\texttt{#1}\xspace}
\renewcommand{\blobstyle}[1]{\texttt{#1}\xspace}
\renewcommand{\methodstyle}[1]{\texttt{#1}\xspace}
\renewcommand{\vocstyle}[1]{\texttt{#1}\xspace}
\renewcommand{\blinder}[1][]{\texttt{blinder}\xspace}
\renewcommand{\msg}[1][]{\texttt{message}\xspace}
\renewcommand{\enc}[1][]{\texttt{ciphertext}\xspace}
\renewcommand{\pk}[1][]{\texttt{pk}\xspace}
\renewcommand{\sk}[1][]{\texttt{sk}\xspace}
\renewcommand{\conc}{||}
\renewcommand{\F}{\mathbb{F}\xspace}
EOF

# Support extensionless \includegraphics{...} paths by adding safe aliases.
# Prefer true image formats and avoid source formats like .mmd/.drawio.
if [[ -d "$TMP_TEX_ROOT/figures" ]]; then
  declare -A FIGURE_BASES=()
  while IFS= read -r -d '' figure_file; do
    FIGURE_BASES["${figure_file%.*}"]=1
  done < <(find "$TMP_TEX_ROOT/figures" -maxdepth 1 -type f -print0)

  for figure_base in "${!FIGURE_BASES[@]}"; do
    [[ -e "$figure_base" ]] && continue
    for ext in png jpg jpeg webp svg pdf; do
      if [[ -f "${figure_base}.${ext}" ]]; then
        ln -s "$(basename "${figure_base}.${ext}")" "$figure_base"
        break
      fi
    done
  done
fi

(
  cd "$TMP_TEX_ROOT/build"
  latexpand --makeatletter main.tex > "$ROOT_DIR/build/flat/flattened.tex"
)

# Preserve references as readable labels when TeX crossrefs are unresolved.
perl -0777 -i -pe '
  s#\{../figures/#\{texsrc/figures/#g;
  s/\\labelcref\{([^}]+)\}/$1/g;
  s/\\eqref\{([^}]+)\}/$1/g;
  s/\\ref\{([^}]+)\}/$1/g;
  s/\\Cref\{([^}]+)\}/$1/g;
  s/\\cref\{([^}]+)\}/$1/g;
  s/\{\\sf\{([^{}]+)\}\}/\\texttt{$1}/g;
  s/\\sf\{([^{}]+)\}/\\texttt{$1}/g;
  s/\{\\tt\{([^{}]+)\}\}/\\texttt{$1}/g;
  s/\\tt\{([^{}]+)\}/\\texttt{$1}/g;
' build/flat/flattened.tex

# Ensure extensionless figure paths point to explicit, browser-friendly files.
if [[ -d "$TMP_TEX_ROOT/figures" ]]; then
  declare -A FIGURE_BASES=()
  while IFS= read -r -d '' figure_file; do
    FIGURE_BASES["$(basename "${figure_file%.*}")"]=1
  done < <(find "$TMP_TEX_ROOT/figures" -maxdepth 1 -type f -print0)

  for figure_base in "${!FIGURE_BASES[@]}"; do
    selected_ext=""
    for ext in png jpg jpeg webp svg pdf; do
      if [[ -f "$TMP_TEX_ROOT/figures/${figure_base}.${ext}" ]]; then
        selected_ext="$ext"
        break
      fi
    done
    [[ -n "$selected_ext" ]] || continue

    escaped_base="$(printf '%s' "texsrc/figures/${figure_base}" | sed -e 's/[][(){}.^$*+?|\\/]/\\&/g')"
    perl -0777 -i -pe "s#\\{${escaped_base}\\}#\\{texsrc/figures/${figure_base}.${selected_ext}\\}#g" build/flat/flattened.tex
  done
fi
