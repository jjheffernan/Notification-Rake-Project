-- Cars & Bids enthusiast auction source

INSERT INTO listings.source (name, base_url, country_code) VALUES
    ('carsandbids', 'https://carsandbids.com', 'US')
ON CONFLICT (name) DO UPDATE SET
    base_url = EXCLUDED.base_url,
    country_code = EXCLUDED.country_code;
