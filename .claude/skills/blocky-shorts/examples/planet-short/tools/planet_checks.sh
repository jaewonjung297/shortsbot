#!/usr/bin/env bash
# Numeric checks of the Short (lens inside things, blocked views, overlaps, framing). Exit 1 if anything FAILs.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d node_modules ] || { echo "node_modules not found: run npm ci first" >&2; exit 2; }
mkdir -p out
npx --no-install esbuild tools/planet_check.ts --bundle --platform=node --format=esm --jsx=automatic --outfile=out/planet_check.mjs --log-level=error
node out/planet_check.mjs
