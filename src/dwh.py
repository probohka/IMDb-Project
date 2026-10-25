"""Batch ELT: flatten the MongoDB `movies` collection into PostgreSQL tables (Neon) for SQL/BI analytics."""

import csv
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from db import get_db

load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
CENTROIDS_FILE = SCHEMA_FILE.with_name("country_centroids.csv")
DWH_URL = os.environ.get("DWH_URL")


def flatten(docs: list) -> tuple:
    """Mongo documents -> row lists for the four tables."""
    movies, genres, directors, markets = [], [], [], []
    for d in docs:
        t = d["_id"]
        movies.append(
            (
                t,
                d["title"],
                d["year"],
                d["decade"],
                d.get("runtimeMinutes"),
                d["rating"],
                d["numVotes"],
            )
        )
        genres += [(t, g) for g in set(d.get("genres", []))]
        directors += [(t, x) for x in set(d.get("directors", []))]
        markets += [(t, r) for r in set(d.get("markets", []))]
    return movies, genres, directors, markets


def copy_rows(cur: psycopg.Cursor, table: str, columns: str, rows: list) -> None:
    with cur.copy(f"COPY {table} ({columns}) FROM STDIN") as copy:
        for row in rows:
            copy.write_row(row)


def load_to_postgres(docs: list) -> None:
    movies, genres, directors, markets = flatten(docs)

    # One transaction: BI never sees empty or half-loaded tables.
    with psycopg.connect(DWH_URL) as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
        cur.execute("TRUNCATE movie_market, movie_director, movie_genre, dim_movie")
        copy_rows(
            cur,
            "dim_movie",
            "tconst, title, year, decade, runtime_minutes, rating, num_votes",
            movies,
        )
        copy_rows(cur, "movie_genre", "tconst, genre", genres)
        copy_rows(cur, "movie_director", "tconst, director", directors)
        copy_rows(cur, "movie_market", "tconst, region", markets)

        cur.execute("TRUNCATE country_centroids")
        with CENTROIDS_FILE.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(line for line in f if not line.startswith("#"))
            copy_rows(
                cur,
                "country_centroids",
                "region, country_name, lat, lon, kind",
                [
                    (r["region"], r["country_name"], r["lat"], r["lon"], r["kind"])
                    for r in reader
                ],
            )

    print(
        f"Loaded into PostgreSQL: {len(movies)} movies, {len(genres)} genres, "
        f"{len(directors)} directors, {len(markets)} markets"
    )


def run() -> None:
    if not DWH_URL:
        sys.exit("DWH_URL is not set (Neon connection string)")

    docs = list(get_db().movies.find({}))
    print(f"Read from MongoDB: {len(docs)} movies")
    if not docs:
        print("movies collection is empty — run src/etl.py first")
        return

    load_to_postgres(docs)


if __name__ == "__main__":
    run()
