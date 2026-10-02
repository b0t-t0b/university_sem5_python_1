#!/usr/bin/env bash
set -e
echo "========================================================"
echo "Practical Work 1 - Variant 22 (RTU MIREA)"
echo "========================================================"
echo ""
echo "[1/4] Checking code style with flake8..."
python -m flake8 --max-line-length=79 src tests
echo "[OK] Code style conforms to PEP8 and rules."
echo ""
echo "[2/4] Running REPL demonstration..."
python -m src.demo_repl
echo ""
echo "[3/4] Running TCP RPC client/server demonstration..."
python -m src.demo_client
echo ""
echo "[4/4] Running Model-Based Testing with Hypothesis and Coverage..."
python -m coverage run --branch -m pytest tests/test_mbt.py -v
python -m coverage report -m
echo ""
echo "========================================================"
echo "All verification steps completed successfully!"
echo "========================================================"
