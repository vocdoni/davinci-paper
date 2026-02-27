#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <output-dir> <file> [file...]" >&2
  exit 1
fi

OUTPUT_DIR="$1"
shift
MEDIA_DIR="$OUTPUT_DIR/media"

escape_regex() {
  printf '%s' "$1" | sed -e 's/[][(){}.^$*+?|\\/]/\\&/g'
}

escape_replacement() {
  printf '%s' "$1" | sed -e 's/[\\/&]/\\&/g'
}

replace_path() {
  local target_file="$1"
  local from_path="$2"
  local to_path="$3"
  local from_escaped to_escaped
  from_escaped="$(escape_regex "$from_path")"
  to_escaped="$(escape_replacement "$to_path")"
  perl -0777 -i -pe "s#${from_escaped}(?=[\\\"'\\)\\s>])#${to_escaped}#g" "$target_file"
}

# Convert PDFs to PNG for browser-friendly rendering.
if [[ -d "$MEDIA_DIR" ]] && command -v pdftoppm >/dev/null 2>&1; then
  while IFS= read -r -d '' pdf_file; do
    png_file="${pdf_file%.pdf}.png"
    if [[ ! -f "$png_file" ]]; then
      pdftoppm -singlefile -png "$pdf_file" "${pdf_file%.pdf}" >/dev/null 2>&1 || true
    fi
  done < <(find "$MEDIA_DIR" -type f -name '*.pdf' -print0)
fi

# Ensure extensionless media files also have stable, browser-friendly suffixes.
if [[ -d "$MEDIA_DIR" ]] && command -v file >/dev/null 2>&1; then
  while IFS= read -r -d '' raw_file; do
    mime_type="$(file -b --mime-type "$raw_file" || true)"
    case "$mime_type" in
      image/png) normalized_file="${raw_file}.png" ;;
      image/jpeg) normalized_file="${raw_file}.jpg" ;;
      image/webp) normalized_file="${raw_file}.webp" ;;
      image/svg+xml) normalized_file="${raw_file}.svg" ;;
      application/pdf) normalized_file="${raw_file}.pdf" ;;
      text/plain) normalized_file="${raw_file}.txt" ;;
      *) continue ;;
    esac
    [[ -f "$normalized_file" ]] || cp "$raw_file" "$normalized_file"
  done < <(find "$MEDIA_DIR" -type f ! -name '*.*' -print0)
fi

for target_file in "$@"; do
  [[ -f "$target_file" ]] || continue

  # Replace embeds with imgs and drop hard-coded sizing attributes.
  perl -0777 -i -pe '
    s#<embed\b#<img#g;
    s#\sstyle="[^"]*(?:width|height):[^"]*"##g;
    s#\sstyle='\''[^'\'']*(?:width|height):[^'\'']*'\''##g;
    s#\swidth="[^"]*"##g;
    s#\sheight="[^"]*"##g;
  ' "$target_file"

  # Rewrite .pdf links to .png only where PNG counterparts exist.
  if [[ -d "$MEDIA_DIR" ]]; then
    while IFS= read -r -d '' png_file; do
      rel_png="${png_file#"$MEDIA_DIR"/}"
      rel_base="${rel_png%.png}"
      replace_path "$target_file" "media/${rel_base}.pdf" "media/${rel_png}"
    done < <(find "$MEDIA_DIR" -type f -name '*.png' -print0)

    # Rewrite extensionless media paths to explicit extensions.
    while IFS= read -r -d '' explicit_file; do
      rel_explicit="${explicit_file#"$MEDIA_DIR"/}"
      rel_base="${rel_explicit%.*}"
      replace_path "$target_file" "media/${rel_base}" "media/${rel_explicit}"
    done < <(find "$MEDIA_DIR" -type f \( -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.webp' -o -name '*.svg' -o -name '*.pdf' -o -name '*.txt' \) -print0)

    # If pandoc emitted .so payload links, redirect to PNG when possible.
    while IFS= read -r -d '' so_file; do
      rel_so="${so_file#"$MEDIA_DIR"/}"
      base_file="${so_file%.so}"
      if [[ -f "${base_file}.png" ]]; then
        replace_path "$target_file" "media/${rel_so}" "media/${rel_so%.so}.png"
      elif [[ -f "${base_file}.txt" ]]; then
        replace_path "$target_file" "media/${rel_so}" "media/${rel_so%.so}.txt"
      fi
    done < <(find "$MEDIA_DIR" -type f -name '*.so' -print0)
  fi
done

# Remove stale .so blobs from published assets. They are not needed for rendering.
if [[ -d "$MEDIA_DIR" ]]; then
  find "$MEDIA_DIR" -type f -name '*.so' -delete
fi
