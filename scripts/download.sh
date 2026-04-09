#!/bin/bash
# Download all data and models needed for this environment.
#
# Estimated total download size: ~5 MB (Python wheels only)
# Estimated disk usage after extraction: ~20 MB
#
# QRandomParity instances are generated procedurally, so there are no external
# datasets or pretrained models to fetch. The only required network step is
# ensuring the Python dependencies are available in the environment overlay.

set -e

cd /home/user

# Install Python dependencies into the system environment overlay.
uv pip install --system highspy numpy

echo "Download/setup complete. QRandomParity instances are generated procedurally."
