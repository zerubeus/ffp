-- FFP Database Initialization Script
-- Creates tables for the Telegram to X bridge application

-- Create posted_messages table
CREATE TABLE IF NOT EXISTS posted_messages (
    id SERIAL PRIMARY KEY,
    telegram_message_id BIGINT UNIQUE NOT NULL,
    twitter_tweet_id VARCHAR(255),
    telegram_channel VARCHAR(255) NOT NULL,
    message_text TEXT,
    media_type VARCHAR(50),
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'posted'
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_telegram_message_id ON posted_messages(telegram_message_id);
CREATE INDEX IF NOT EXISTS idx_posted_at ON posted_messages(posted_at DESC);

-- Create error_log table
CREATE TABLE IF NOT EXISTS error_log (
    id SERIAL PRIMARY KEY,
    telegram_message_id BIGINT,
    error_message TEXT,
    error_type VARCHAR(100),
    occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for error log
CREATE INDEX IF NOT EXISTS idx_error_occurred_at ON error_log(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_error_telegram_message_id ON error_log(telegram_message_id);

-- Create statistics view for monitoring
CREATE OR REPLACE VIEW posting_statistics AS
SELECT 
    DATE(posted_at) as date,
    COUNT(*) as posts_count,
    COUNT(DISTINCT telegram_channel) as channels_count,
    COUNT(CASE WHEN media_type IS NOT NULL THEN 1 END) as media_posts_count
FROM posted_messages
GROUP BY DATE(posted_at)
ORDER BY date DESC;

-- Grant permissions (if needed in production)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ffp;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ffp;