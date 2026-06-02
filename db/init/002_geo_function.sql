-- Geo query helper for Hasura native queries / SQL functions
CREATE OR REPLACE FUNCTION public.listings_within_radius(
    origin_lon double precision,
    origin_lat double precision,
    radius_m double precision DEFAULT 50000
)
RETURNS TABLE (
    id uuid,
    title text,
    price numeric,
    year integer,
    make text,
    model text,
    meters double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT vl.id, vl.title, vl.price, vl.year,
           mk.name AS make, mo.name AS model,
           ST_Distance(
               vl.geom,
               ST_SetSRID(ST_MakePoint(origin_lon, origin_lat), 4326)::geography
           ) AS meters
    FROM vehicle_listing vl
    LEFT JOIN vehicle_make mk ON mk.id = vl.make_id
    LEFT JOIN vehicle_model mo ON mo.id = vl.model_id
    WHERE ST_DWithin(
        vl.geom,
        ST_SetSRID(ST_MakePoint(origin_lon, origin_lat), 4326)::geography,
        radius_m
    )
    ORDER BY meters;
$$;
