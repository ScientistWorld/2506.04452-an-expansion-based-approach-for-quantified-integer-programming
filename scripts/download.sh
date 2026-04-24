#!/bin/bash
# Download all data and models needed for this environment.
#
# Estimated total download size: <1 MB
# Estimated disk usage after extraction: <1 MB
#
# QRandomParity instances are generated procedurally, but the official EQuIPS
# release includes small sample `.qlp` instances used here to validate the
# optimization path on paper-provided inputs. Python dependencies are installed
# via environment/setup.sh, not this script.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

mkdir -p data/downloads

if [ ! -d data/downloads/EQuIPS ]; then
    git clone --depth 1 https://github.com/MichaelHartisch/EQuIPS.git data/downloads/EQuIPS
fi

echo "Downloads ready:"
echo "  - Official EQuIPS sample instances in data/downloads/EQuIPS"
