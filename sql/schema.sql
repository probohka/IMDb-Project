-- DWH schema (Neon PostgreSQL). Source: the `movies` collection in MongoDB.
-- Full refresh on every run: tables are truncated and reloaded inside one transaction.

CREATE TABLE IF NOT EXISTS dim_movie (
    tconst          TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    year            SMALLINT NOT NULL,
    decade          SMALLINT NOT NULL,
    runtime_minutes SMALLINT,
    rating          NUMERIC(3, 1) NOT NULL,
    num_votes       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS movie_genre (
    tconst TEXT NOT NULL REFERENCES dim_movie (tconst) ON DELETE CASCADE,
    genre  TEXT NOT NULL,
    PRIMARY KEY (tconst, genre)
);

CREATE TABLE IF NOT EXISTS movie_director (
    tconst   TEXT NOT NULL REFERENCES dim_movie (tconst) ON DELETE CASCADE,
    director TEXT NOT NULL,
    PRIMARY KEY (tconst, director)
);

-- Localization proxy (imdbDisplay regions of title.akas), not real box office.
CREATE TABLE IF NOT EXISTS movie_market (
    tconst TEXT NOT NULL REFERENCES dim_movie (tconst) ON DELETE CASCADE,
    region TEXT NOT NULL,
    PRIMARY KEY (tconst, region)
);

-- Country centroids (ISO 3166-1 alpha-2) for map charts; loaded from sql/country_centroids.csv.
CREATE TABLE IF NOT EXISTS country_centroids (
    region       TEXT PRIMARY KEY,
    country_name TEXT NOT NULL,
    lat          DOUBLE PRECISION NOT NULL,
    lon          DOUBLE PRECISION NOT NULL
);

-- Marts: plain views for BI (always fresh, no REFRESH needed after the full reload).

CREATE OR REPLACE VIEW mart_genre_by_decade AS
SELECT
    g.genre,
    m.decade,
    count(*)                 AS movies,
    round(avg(m.rating), 2)  AS avg_rating,
    sum(m.num_votes)         AS total_votes
FROM movie_genre g
JOIN dim_movie m USING (tconst)
GROUP BY g.genre, m.decade;

CREATE OR REPLACE VIEW mart_genre_by_year AS
SELECT
    g.genre,
    m.year,
    count(*)                 AS movies,
    round(avg(m.rating), 2)  AS avg_rating,
    sum(m.num_votes)         AS total_votes
FROM movie_genre g
JOIN dim_movie m USING (tconst)
GROUP BY g.genre, m.year;

CREATE OR REPLACE VIEW mart_director_stats AS
SELECT
    d.director,
    count(*)                 AS movies,
    round(avg(m.rating), 2)  AS avg_rating,
    sum(m.num_votes)         AS total_votes,
    min(m.year)              AS first_year,
    max(m.year)              AS last_year
FROM movie_director d
JOIN dim_movie m USING (tconst)
GROUP BY d.director;

-- Localization proxy by region and year (see movie_market), not real box office.
CREATE OR REPLACE VIEW mart_markets_by_year AS
SELECT
    k.region,
    m.year,
    count(*)                 AS movies,
    round(avg(m.rating), 2)  AS avg_rating
FROM movie_market k
JOIN dim_movie m USING (tconst)
GROUP BY k.region, m.year;

-- Localization proxy per country with coordinates, for the DataLens map (geopoints).
-- Non-country codes (XWW, XEU, SUHH, ...) have no centroid and drop out via the inner join.
CREATE OR REPLACE VIEW mart_markets_geo AS
SELECT
    c.region,
    c.country_name,
    c.lat,
    c.lon,
    count(*)                 AS movies,
    round(avg(m.rating), 2)  AS avg_rating
FROM movie_market k
JOIN country_centroids c USING (region)
JOIN dim_movie m USING (tconst)
GROUP BY c.region, c.country_name, c.lat, c.lon;

-- One row per movie: list attributes aggregated per movie so joins can't multiply rows.
CREATE OR REPLACE VIEW mart_movies_flat AS
SELECT
    m.tconst,
    m.title,
    m.year,
    m.decade,
    m.runtime_minutes,
    m.rating,
    m.num_votes,
    (SELECT string_agg(g.genre, ', ' ORDER BY g.genre)
       FROM movie_genre g WHERE g.tconst = m.tconst)      AS genres,
    (SELECT string_agg(d.director, ', ' ORDER BY d.director)
       FROM movie_director d WHERE d.tconst = m.tconst)   AS directors,
    (SELECT count(*) FROM movie_market k WHERE k.tconst = m.tconst) AS markets_count
FROM dim_movie m;

CREATE INDEX IF NOT EXISTS idx_dim_movie_year ON dim_movie (year);
CREATE INDEX IF NOT EXISTS idx_movie_genre_genre ON movie_genre (genre);
CREATE INDEX IF NOT EXISTS idx_movie_director_director ON movie_director (director);
CREATE INDEX IF NOT EXISTS idx_movie_market_region ON movie_market (region);
