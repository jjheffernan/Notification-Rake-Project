-- Scheduled vehicle searches — server-side watchlist with interval + ingest refresh

ALTER TABLE metadata.saved_search
    ADD COLUMN IF NOT EXISTS profile_id UUID,
    ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS interval_minutes INT NOT NULL DEFAULT 360,
    ADD COLUMN IF NOT EXISTS ingest_routes JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_match_count INT,
    ADD COLUMN IF NOT EXISTS last_new_count INT,
    ADD COLUMN IF NOT EXISTS last_seen_ids JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS saved_search_profile_idx ON metadata.saved_search (profile_id);
CREATE INDEX IF NOT EXISTS saved_search_next_run_idx ON metadata.saved_search (next_run_at)
    WHERE enabled = true;
