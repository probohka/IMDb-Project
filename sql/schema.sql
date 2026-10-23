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

CREATE INDEX IF NOT EXISTS idx_dim_movie_year ON dim_movie (year);
CREATE INDEX IF NOT EXISTS idx_movie_genre_genre ON movie_genre (genre);
CREATE INDEX IF NOT EXISTS idx_movie_director_director ON movie_director (director);
CREATE INDEX IF NOT EXISTS idx_movie_market_region ON movie_market (region);
