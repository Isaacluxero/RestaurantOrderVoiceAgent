#!/bin/bash
set -e

echo "🔨 Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "✅ Build complete!"

