#!/bin/bash
# Download all data and models needed for this environment.
#
# Estimated total download size: 0 MB
# Estimated disk usage after extraction: 0 MB
#
# QRandomParity instances are generated procedurally, so there are no external
# datasets, pretrained models, or paper-specific artifacts to fetch here.
# Python dependencies are installed via environment/setup.sh, not this script.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p data/downloads

echo "No downloads required. QRandomParity instances are generated procedurally."
