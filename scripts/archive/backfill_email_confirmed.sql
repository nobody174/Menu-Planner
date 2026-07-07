-- Mark all unconfirmed users as confirmed (grandfathering)
-- Use with: railway run psql -f scripts/backfill_email_confirmed.sql
-- Useful when deploying email confirmation feature without blocking existing users

UPDATE users
SET email_confirmed_at = NOW()
WHERE email_confirmed_at IS NULL;

-- Verify backfill
SELECT COUNT(*) as confirmed_users FROM users WHERE email_confirmed_at IS NOT NULL;
