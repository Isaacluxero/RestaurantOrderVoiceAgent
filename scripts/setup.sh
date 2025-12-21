#!/bin/bash
# Setup script for AI Voice Agent

set -e

echo "Setting up AI Voice Agent..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "Poetry is not installed. Please install it first:"
    echo "curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Install dependencies
echo "Installing dependencies..."
poetry install

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration"
else
    echo ".env file already exists"
fi

# Run database migrations
echo "Running database migrations..."
poetry run alembic upgrade head

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys and configuration"
echo "2. Run: poetry run uvicorn app.main:app --reload"
echo "3. Configure your Twilio phone number to point to: http://your-server/webhooks/voice/incoming"

