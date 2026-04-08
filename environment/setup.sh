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
# Use: python3 -m pip install (pip3 is broken under fakeroot in container.def)
# Do NOT create a venv (python -m venv, virtualenv, etc.).

set -e

# Install highspy (HiGHS Python bindings) — open-source IP/MIP solver
# HiGHS is the IP solver backend used by EQuIPS
python3 -m pip install --no-cache-dir highspy numpy
