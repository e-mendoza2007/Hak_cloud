#!/usr/bin/env bash
# Construye el layer con google-auth + requests (solo se hace una vez).
set -e
rm -rf layer/gcp/python && mkdir -p layer/gcp/python
pip install --target layer/gcp/python --platform manylinux2014_x86_64 --implementation cp \
    --python-version 3.12 --only-binary=:all: --upgrade -r layer/requirements.txt
echo "Layer listo en layer/gcp/python"
