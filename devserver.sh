#!/bin/bash

# Ensure we're using poetry-managed environment
poetry install

# Set environment variables
export FLASK_DEBUG=1
export PORT=${PORT:-5001}
export FLASK_APP="app.main:create_app"

echo "Development server starting on PORT: $PORT with DEBUG=$FLASK_DEBUG"

# Run Flask app using Poetry's environment
poetry run python -m flask run -p $PORT --debug