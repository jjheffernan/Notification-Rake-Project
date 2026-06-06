-- UK / Germany marketplace sources (eBay, Gumtree, AutoScout24, mobile.de, Copart EU)

INSERT INTO listings.source (name, base_url, country_code) VALUES
    ('ebay_uk', 'https://www.ebay.co.uk', 'GB'),
    ('gumtree', 'https://www.gumtree.com', 'GB'),
    ('autoscout24_uk', 'https://www.autoscout24.co.uk', 'GB'),
    ('copart_uk', 'https://www.copart.co.uk', 'GB'),
    ('mobile_de', 'https://www.mobile.de', 'DE'),
    ('autoscout24_de', 'https://www.autoscout24.de', 'DE'),
    ('ebay_de', 'https://www.ebay.de', 'DE'),
    ('copart_de', 'https://www.copart.de', 'DE')
ON CONFLICT (name) DO UPDATE SET
    base_url = EXCLUDED.base_url,
    country_code = EXCLUDED.country_code;
