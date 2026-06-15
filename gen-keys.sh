#!/usr/bin/env bash
set -euo pipefail

# Erzeugt zufaellige API-Keys (openssl rand -hex 16) und schreibt eine fertige
# API_KEYS=...-Zeile (kommagetrennt) nach keys.txt.
#
# Nutzung:  ./gen-keys.sh [anzahl]   (Default 20, die App akzeptiert max. 100)

count="${1:-20}"
out="keys.txt"

keys=()
for ((i = 0; i < count; i++)); do
  keys+=("$(openssl rand -hex 16)")
done

# Keys mit Kommas verbinden.
joined=$(IFS=,; echo "${keys[*]}")

printf 'API_KEYS=%s\n' "$joined" > "$out"
chmod 600 "$out"   # Secrets: nur fuer den Eigentuemer lesbar

echo "$count API-Keys erzeugt -> $out"
