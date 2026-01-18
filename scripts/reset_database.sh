#!/bin/bash
# Reset PostgreSQL database - removes all data but keeps schema
# Usage: ./scripts/reset_database.sh

set -e

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "Error: DATABASE_URL environment variable is not set"
    echo "Please set it with: export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    exit 1
fi

echo "⚠️  WARNING: This will delete ALL data from the database!"
echo "Tables: order_items, orders, calls"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cancelled."
    exit 0
fi

echo "Resetting database..."
psql "$DATABASE_URL" -f scripts/reset_database.sql

echo "✅ Database reset complete! All tables are now empty."
