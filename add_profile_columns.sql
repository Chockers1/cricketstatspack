-- Add display_name column if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(255) DEFAULT NULL;

-- Add notify_newsletter column if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_newsletter TINYINT(1) NOT NULL DEFAULT 0;
