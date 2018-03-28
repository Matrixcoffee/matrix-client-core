#!/bin/sh

PYTHONPATH=.:../urllib-requests-adapter:../matrix-python-sdk python3 TestClient.py "$@"
