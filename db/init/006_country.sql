-- Country / region on search layer + source registry
ALTER TABLE vehicle_listing
    ADD COLUMN IF NOT EXISTS country TEXT;

CREATE INDEX IF NOT EXISTS vehicle_listing_country_idx ON vehicle_listing (country);

ALTER TABLE listings.source
    ADD COLUMN IF NOT EXISTS country_code TEXT;

UPDATE listings.source SET country_code = 'US' WHERE name = 'craigslist';

INSERT INTO listings.source (name, base_url, country_code) VALUES
    ('yahoo_auctions_jp', 'https://auctions.yahoo.co.jp', 'JP')
ON CONFLICT (name) DO UPDATE SET country_code = EXCLUDED.country_code;

UPDATE vehicle_listing SET country = 'US'
WHERE country IS NULL AND source = 'craigslist';

UPDATE vehicle_listing SET country = 'JP'
WHERE country IS NULL AND source = 'yahoo_auctions_jp';
