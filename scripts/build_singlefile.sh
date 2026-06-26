#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/engine/dist"

mkdir -p "$DIST"

npx esbuild "$ROOT/engine/single-file-hooks-frames.js" \
  --bundle --format=iife \
  --outfile="$DIST/hook.bundle.js"

npx esbuild "$ROOT/engine/playwright-entry.js" \
  --bundle --format=iife \
  --outfile="$DIST/singlefile.bundle.js"

echo "Built SingleFile bundles in engine/dist/"
