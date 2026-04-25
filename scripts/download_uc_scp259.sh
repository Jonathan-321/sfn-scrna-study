#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: bash scripts/download_uc_scp259.sh <urls_tsv> [output_dir]" >&2
  exit 1
fi

URLS_TSV="$1"
OUTPUT_DIR="${2:-/Users/jonathanmuhire/CFN/sfn-scrna-study/data/raw/uc_scp259}"

if [[ ! -f "$URLS_TSV" ]]; then
  echo "URLs file not found: $URLS_TSV" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

required_files=(
  "all.meta2.txt"
  "gene_sorted-Epi.matrix.mtx"
  "Epi.genes.tsv"
  "Epi.barcodes2.tsv"
  "gene_sorted-Fib.matrix.mtx"
  "Fib.genes.tsv"
  "Fib.barcodes2.tsv"
  "gene_sorted-Imm.matrix.mtx"
  "Imm.genes.tsv"
  "Imm.barcodes2.tsv"
)

while IFS=$'\t' read -r filename url; do
  [[ -z "${filename}" ]] && continue
  [[ "${filename}" =~ ^# ]] && continue

  if [[ -z "${url:-}" || "$url" == "PASTE_SIGNED_URL_HERE" ]]; then
    echo "Skipping $filename because URL is missing" >&2
    continue
  fi

  dest="$OUTPUT_DIR/$filename"
  echo "Downloading $filename"
  curl -L --fail --output "$dest" "$url"

  if LC_ALL=C head -c 512 "$dest" | grep -Eqi '<!DOCTYPE html|<html|Single Cell Portal'; then
    echo "Downloaded HTML instead of data for $filename" >&2
    echo "Use the signed file URL from the actual download button, not the study page URL." >&2
    exit 3
  fi
done < "$URLS_TSV"

echo
echo "Download directory: $OUTPUT_DIR"

missing=0
for filename in "${required_files[@]}"; do
  if [[ -f "$OUTPUT_DIR/$filename" ]]; then
    size=$(wc -c < "$OUTPUT_DIR/$filename")
    echo "OK  $filename ($size bytes)"
  else
    echo "MISS $filename"
    missing=1
  fi
done

if [[ $missing -ne 0 ]]; then
  echo
  echo "Some required files are still missing." >&2
  exit 2
fi

echo
echo "All required UC benchmark files are present."
