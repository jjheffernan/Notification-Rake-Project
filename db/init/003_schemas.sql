-- Logical database layers (single Postgres instance — see specs.md)
CREATE SCHEMA IF NOT EXISTS reference;
CREATE SCHEMA IF NOT EXISTS listings;
CREATE SCHEMA IF NOT EXISTS metadata;

-- Bridge existing catalog tables into reference schema (read via views)
CREATE OR REPLACE VIEW reference.vehicle_make AS
    SELECT id, name FROM public.vehicle_make;

CREATE OR REPLACE VIEW reference.vehicle_model AS
    SELECT id, make_id, name FROM public.vehicle_model;

-- Extended reference catalog
CREATE TABLE IF NOT EXISTS reference.vehicle_body_style (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS reference.vehicle_generation (
    id SERIAL PRIMARY KEY,
    model_id INT NOT NULL REFERENCES public.vehicle_model(id),
    name TEXT NOT NULL,
    year_start INT,
    year_end INT,
    UNIQUE (model_id, name)
);

CREATE TABLE IF NOT EXISTS reference.vehicle_trim (
    id SERIAL PRIMARY KEY,
    model_id INT NOT NULL REFERENCES public.vehicle_model(id),
    name TEXT NOT NULL,
    body_style_id INT REFERENCES reference.vehicle_body_style(id),
    UNIQUE (model_id, name)
);

INSERT INTO reference.vehicle_body_style (name) VALUES
    ('Sedan'), ('SUV'), ('Truck'), ('Coupe'), ('Hatchback'), ('Wagon')
ON CONFLICT DO NOTHING;

-- Raw marketplace records (preserved for reprocessing)
CREATE TABLE IF NOT EXISTS listings.source (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS listings.seller (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id INT NOT NULL REFERENCES listings.source(id),
    external_id TEXT,
    name TEXT,
    seller_type TEXT,
    UNIQUE (source_id, external_id)
);

CREATE TABLE IF NOT EXISTS listings.listing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id INT NOT NULL REFERENCES listings.source(id),
    external_id TEXT NOT NULL,
    seller_id UUID REFERENCES listings.seller(id),
    title TEXT,
    description TEXT,
    raw_payload JSONB,
    price NUMERIC(12, 2),
    year INT,
    mileage INT,
    vin TEXT,
    url TEXT,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source_id, external_id)
);

CREATE TABLE IF NOT EXISTS listings.listing_image (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings.listing(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    position INT NOT NULL DEFAULT 0,
    UNIQUE (listing_id, url)
);

CREATE TABLE IF NOT EXISTS listings.listing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    listing_id UUID NOT NULL REFERENCES listings.listing(id) ON DELETE CASCADE,
    price NUMERIC(12, 2),
    title TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS listing_history_listing_idx
    ON listings.listing_history (listing_id, recorded_at DESC);

INSERT INTO listings.source (name, base_url) VALUES
    ('craigslist', 'https://www.craigslist.org')
ON CONFLICT (name) DO NOTHING;

-- Operational metadata
CREATE TABLE IF NOT EXISTS metadata.job_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    fetched INT,
    matched INT,
    upserted INT,
    new_listings INT,
    alerted INT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS metadata.crawler_status (
    source_id INT PRIMARY KEY REFERENCES listings.source(id),
    last_run_at TIMESTAMPTZ,
    last_status TEXT,
    listings_seen INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS metadata.sync_status (
    id SERIAL PRIMARY KEY,
    layer TEXT NOT NULL,
    last_sync_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    records_synced INT NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS metadata.api_usage (
    id BIGSERIAL PRIMARY KEY,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'GET',
    status_code INT,
    duration_ms INT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS metadata.system_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    labels JSONB,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS job_runs_started_idx ON metadata.job_runs (started_at DESC);
