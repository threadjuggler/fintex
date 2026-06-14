#!/usr/bin/env bash
set -euo pipefail



rsync -av --exclude='.git' --exclude='__pycache__' /home/bov/python/fintex/ /home/bov/python/x/fintex
