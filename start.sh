#!/bin/bash

# Startup script for AI Voice Agent
# This script builds the frontend and starts the backend server

set -e

echo "🚀 Starting AI Voice Agent..."

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Please install it first:"
    echo "curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check if Node.js is installed (for frontend)
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Please create one with your configuration."
    echo "Required variables:"
    echo "  - OPENAI_API_KEY"
    echo "  - TWILIO_ACCOUNT_SID"
    echo "  - TWILIO_AUTH_TOKEN"
    echo "  - TWILIO_PHONE_NUMBER"
    echo "  - DATABASE_URL"
    exit 1
fi

# Install backend dependencies (skip if core deps are already available)
echo "📦 Checking backend dependencies..."
if poetry run python -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null; then
    echo "✅ Backend dependencies already installed. Skipping installation..."
else
    echo "📦 Installing backend dependencies..."
    set +e  # Temporarily disable exit on error
    poetry install
    INSTALL_EXIT_CODE=$?
    set -e  # Re-enable exit on error

    if [ $INSTALL_EXIT_CODE -ne 0 ]; then
        echo "⚠️  Some dependencies failed to install (likely asyncpg on Python 3.14)"
        echo "This is OK if you're using SQLite. Checking if core dependencies are available..."
        poetry run python -c "import fastapi, uvicorn, sqlalchemy" 2>/dev/null || {
            echo "❌ Core dependencies are missing. Please fix the installation issue."
            exit 1
        }
        echo "✅ Core dependencies are available. Continuing..."
    fi
fi

# Install frontend dependencies if node_modules doesn't exist
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Build frontend
echo "🔨 Building frontend..."
cd frontend
npm run build
cd ..

# Run database migrations
echo "🗄️  Running database migrations..."
poetry run alembic upgrade head

# Start the server
echo "✅ Starting server..."
echo "🌐 Server will be available at http://localhost:8000"
echo "📊 Order history dashboard will be available at http://localhost:8000"
echo ""
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000

