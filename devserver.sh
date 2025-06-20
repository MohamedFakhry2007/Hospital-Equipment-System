#!/bin/sh
export PATH="$HOME/.local/bin:$PATH"

poetry install
source .venv/bin/activate

if ! grep -q "$PATH" /home/user/.bashrc; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> /home/user/.bashrc
fi

# Set DEBUG mode for development
export DEBUG=True

# Get the port number from environment variable, default to 5001 for dev server
PORT=${PORT:-5001}
echo "Development server starting on PORT: $PORT with DEBUG=True"

# Run Flask development server
# Assuming 'create_app' is the factory function in 'app.main'
python -m flask --app app.main:create_app run -p $PORT --debug
