-- Reset PostgreSQL database - removes all data but keeps schema
-- Run this with: psql $DATABASE_URL -f scripts/reset_database.sql
-- Or connect to your database and paste these commands

-- Truncate all tables in the correct order (respecting foreign keys)
-- Using CASCADE to automatically handle dependent tables
TRUNCATE TABLE order_items, orders, calls RESTART IDENTITY CASCADE;

-- Verify tables are empty
SELECT 'order_items' as table_name, COUNT(*) as row_count FROM order_items
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'calls', COUNT(*) FROM calls;
