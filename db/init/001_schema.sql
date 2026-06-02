-- MVP schema: canonical vehicle catalog + geospatial listings
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE vehicle_make (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE vehicle_model (
    id SERIAL PRIMARY KEY,
    make_id INT NOT NULL REFERENCES vehicle_make(id),
    name TEXT NOT NULL,
    UNIQUE (make_id, name)
);

CREATE TABLE vehicle_listing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    source_listing_id TEXT NOT NULL,
    title TEXT,
    description TEXT,
    make_id INT REFERENCES vehicle_make(id),
    model_id INT REFERENCES vehicle_model(id),
    year INT,
    mileage INT,
    price NUMERIC(12, 2),
    vin TEXT,
    geom GEOGRAPHY(POINT, 4326),
    seller_name TEXT,
    seller_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, source_listing_id)
);

CREATE INDEX vehicle_listing_geom_idx ON vehicle_listing USING GIST (geom);
CREATE INDEX vehicle_listing_price_idx ON vehicle_listing (price);
CREATE INDEX vehicle_listing_year_idx ON vehicle_listing (year);

INSERT INTO vehicle_make (name) VALUES ('Toyota'), ('Honda'), ('Ford'), ('Nissan')
ON CONFLICT DO NOTHING;

INSERT INTO vehicle_model (make_id, name)
SELECT mk.id, m.name
FROM vehicle_make mk
JOIN (VALUES
    ('Toyota', 'Camry'),
    ('Toyota', 'Corolla'),
    ('Toyota', 'RAV4'),
    ('Honda', 'Civic'),
    ('Honda', 'Accord'),
    ('Ford', 'F-150'),
    ('Nissan', 'Altima'),
    ('Nissan', 'Stagea')
) AS m(make_name, name) ON mk.name = m.make_name
ON CONFLICT DO NOTHING;
