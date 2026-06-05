-- Copart source, auction extensions, buyer account connectors

INSERT INTO listings.source (name, base_url, country_code) VALUES
    ('copart', 'https://www.copart.com', 'US'),
    ('ebay', 'https://www.ebay.com', 'US')
ON CONFLICT (name) DO UPDATE SET
    base_url = EXCLUDED.base_url,
    country_code = EXCLUDED.country_code;

CREATE TABLE IF NOT EXISTS listings.auction_lot (
    listing_id UUID PRIMARY KEY REFERENCES listings.listing(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    lot_number TEXT NOT NULL,
    auction_status TEXT,
    ends_at TIMESTAMPTZ,
    primary_damage TEXT,
    secondary_damage TEXT,
    loss_type TEXT,
    run_and_drive BOOLEAN,
    has_keys BOOLEAN,
    title_type TEXT,
    bid_count INT,
    analysis JSONB NOT NULL DEFAULT '{}',
    UNIQUE (platform, lot_number)
);

CREATE INDEX IF NOT EXISTS auction_lot_platform_status_idx
    ON listings.auction_lot (platform, auction_status);

CREATE TABLE IF NOT EXISTS metadata.connected_account (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL,
    provider TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT '',
    config JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT true,
    last_sync_at TIMESTAMPTZ,
    last_status TEXT,
    listings_synced INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (profile_id, provider, label)
);

CREATE INDEX IF NOT EXISTS connected_account_profile_idx
    ON metadata.connected_account (profile_id);
