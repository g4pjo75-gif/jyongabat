#!/usr/bin/env bash
# exit on error
set -o errexit

echo "--- Installing Python dependencies ---"
pip install -r requirements.txt

echo "--- Building Frontend ---"
cd frontend
npm install
npm run build
cd ..

echo "--- Preparing Data Directory ---"
mkdir -p data

echo "--- Build Completed ---"
