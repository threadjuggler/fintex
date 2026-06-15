#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <username>" >&2
  exit 1
fi

user="$1"

# Lokale Artefakte + Secrets nicht mitschicken. Der Server haelt sein eigenes .env.
rsync -av \
  --exclude='.git' \
  --exclude='instructions' \
  --exclude='__pycache__' \
  --exclude='.venv' \
  --exclude='.env' \
  --exclude='keys.txt' \
  --exclude='zielliste.md' \
  --exclude='nodeeps-www' \
  --exclude='.pytest_cache' \
  --exclude='.ruff_cache' \
  /home/bov/python/fintex/ "${user}@api.snapvoice.de:~/fintex/"
