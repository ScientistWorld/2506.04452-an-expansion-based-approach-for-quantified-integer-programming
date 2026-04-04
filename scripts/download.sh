#!/bin/bash
# Download all data and models needed for this environment.
#
# EQuIPS uses HiGHS as the IP solver backend.
# HiGHS is installed via pip (highspy package).
# No external datasets or models are needed — all QRandomParity instances
# are generated procedurally.
#
# Estimated total download size: ~5 MB (numpy + highspy)
# Estimated disk usage after extraction: ~20 MB
#
# Run on a node with internet access BEFORE building the container
# or submitting compute jobs.

set -e

cd "$(dirname "$0")"

# Install highspy and numpy (HiGHS Python bindings)
# These provide the IP solver backend for EQuIPS
pip install highspy numpy

echo "Download/setup complete. EQuIPS will generate QRandomParity instances procedurally."
