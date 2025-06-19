#!/bin/bash

echo "Setting up Hospital Equipment Maintenance App..."

# Ensure current directory is in Python path
export PYTHONPATH=$(pwd)

echo "Installing dependencies with Poetry..."
poetry install

echo "Creating .env file from .env.example..."
cp -n .env.example .env || true

echo "Ensuring data directory exists..."
mkdir -p data

echo "Starting Gunicorn server..."
echo "PORT is: ${PORT}"

# Run Gunicorn with 2 workers, binding to 0.0.0.0:$PORT
poetry run gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2
