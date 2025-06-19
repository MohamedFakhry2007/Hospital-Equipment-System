#!/bin/bash

# Setting up Hospital Equipment Maintenance App...
echo "Setting up Hospital Equipment Maintenance App..."

# Install dependencies with Poetry
echo "Installing dependencies with Poetry..."
poetry install --no-interaction --no-ansi

# Creating .env file from .env.example if it doesn't exist
if [ ! -f .env ]; then
  echo "Creating .env file from .env.example..."
  cp .env.example .env
fi

# Ensure data directory exists
mkdir -p data
echo "Ensuring data directory exists..."

# Starting Gunicorn server
echo "Starting Gunicorn server..."

# Get the port number from environment variable, default to 5000
PORT=${PORT:-5000}
echo "PORT is: $PORT"

# Run Gunicorn.  Tell it to call the create_app() function in app/main.py
poetry run gunicorn 'app:create_app()' \
    --bind 0.0.0.0:${PORT} \
    --workers 2 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug