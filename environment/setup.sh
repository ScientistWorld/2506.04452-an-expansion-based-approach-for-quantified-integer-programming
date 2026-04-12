#!/bin/bash
# Install Python packages into the container overlay.
#
# This script is run by the system on the login node (which has internet)
# inside the container with a persistent overlay. Changes persist across
# job submissions without rebuilding the container.
#
# IMPORTANT: Install into the SYSTEM Python, not a virtual environment.
# The overlay may be recreated on container rebuilds — a venv inside
# it will be lost and all subsequent jobs will fail.
# Use: uv pip install --system
# Do NOT create a venv (python -m venv, virtualenv, etc.).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEEL_DIR="${SCRIPT_DIR}/wheels"

# Install vendored cp311 wheels to avoid long setup-time network resolution
# or source builds. HiGHS is the default LP/MIP backend; OR-Tools CP-SAT is
# additionally installed for the universal wins1 subproblems in auto mode.
uv pip install --system \
    "${WHEEL_DIR}/numpy-2.2.6-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl" \
    "${WHEEL_DIR}/highspy-1.11.0-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl" \
    "ortools>=9.9,<10"
