-- Delete all test users and related data from the database
-- Use with: railway run psql -f scripts/delete_test_users.sql
-- WARNING: This is destructive and cannot be undone. Use only when intentional.

DELETE FROM household_members;
DELETE FROM households;
DELETE FROM users;

-- Verify deletion
SELECT COUNT(*) as remaining_users FROM users;
