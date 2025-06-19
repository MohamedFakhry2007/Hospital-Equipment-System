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

echo "Starting Flask application..."
echo "PORT is: ${PORT}"
poetry run start-app
