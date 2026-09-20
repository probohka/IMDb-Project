"""Построение аналитической коллекции фильмов IMDb и загрузка в MongoDB (для MongoDB Charts)."""

import os
from pathlib import Path

import pandas as pd

from db import get_db

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Полный IMDb не влезет в бесплатный тир Atlas (512MB) — отсекаем малозаметные тайтлы.
MIN_VOTES = int(os.environ.get("MIN_VOTES", 500))
MIN_YEAR = int(os.environ.get("MIN_YEAR", 1900))
CHUNK_SIZE = 200_000


def load_movies() -> pd.DataFrame:
    basics = pd.read_csv(
        RAW_DIR / "title.basics.tsv.gz",
        sep="\t",
        na_values="\\N",
        dtype=str,
        usecols=[
            "tconst",
            "titleType",
            "primaryTitle",
            "startYear",
            "runtimeMinutes",
            "genres",
        ],
    )
    basics = basics[basics["titleType"] == "movie"].copy()
    basics["startYear"] = pd.to_numeric(basics["startYear"], errors="coerce")
    basics["runtimeMinutes"] = pd.to_numeric(basics["runtimeMinutes"], errors="coerce")
    basics = basics[basics["startYear"] >= MIN_YEAR]

    ratings = pd.read_csv(
        RAW_DIR / "title.ratings.tsv.gz",
        sep="\t",
        na_values="\\N",
        dtype={"tconst": str, "averageRating": float, "numVotes": "Int64"},
    )
    ratings = ratings[ratings["numVotes"] >= MIN_VOTES]

    return basics.merge(ratings, on="tconst", how="inner")


def load_directors(tconsts: set) -> dict:
    """tconst -> список имён режиссёров. title.principals большой — читаем чанками."""
    director_ids: dict = {}
    reader = pd.read_csv(
        RAW_DIR / "title.principals.tsv.gz",
        sep="\t",
        na_values="\\N",
        dtype=str,
        usecols=["tconst", "nconst", "category"],
        chunksize=CHUNK_SIZE,
    )
    for chunk in reader:
        mask = (chunk["category"] == "director") & chunk["tconst"].isin(tconsts)
        for tconst, nconst in chunk.loc[mask, ["tconst", "nconst"]].itertuples(
            index=False
        ):
            director_ids.setdefault(tconst, []).append(nconst)

    all_nconsts = {n for ids in director_ids.values() for n in ids}
    names = pd.read_csv(
        RAW_DIR / "name.basics.tsv.gz",
        sep="\t",
        na_values="\\N",
        dtype=str,
        usecols=["nconst", "primaryName"],
    )
    name_map = (
        names[names["nconst"].isin(all_nconsts)]
        .set_index("nconst")["primaryName"]
        .to_dict()
    )

    return {
        tconst: [name_map[n] for n in nconsts if n in name_map]
        for tconst, nconsts in director_ids.items()
    }


def build_documents(movies: pd.DataFrame, directors: dict) -> list:
    docs = []
    for row in movies.itertuples(index=False):
        year = int(row.startYear)
        docs.append(
            {
                "_id": row.tconst,
                "title": row.primaryTitle,
                "year": year,
                "decade": year // 10 * 10,
                "genres": row.genres.split(",") if isinstance(row.genres, str) else [],
                "runtimeMinutes": None
                if pd.isna(row.runtimeMinutes)
                else int(row.runtimeMinutes),
                "rating": float(row.averageRating),
                "numVotes": int(row.numVotes),
                "directors": directors.get(row.tconst, []),
            }
        )
    return docs


def load_to_mongo(docs: list) -> None:
    db = get_db()
    db.movies.delete_many({})
    if docs:
        db.movies.insert_many(docs)
    db.movies.create_index("year")
    db.movies.create_index("genres")
    db.movies.create_index("rating")


def run() -> None:
    print(f"Фильтр: startYear >= {MIN_YEAR}, numVotes >= {MIN_VOTES}")

    movies = load_movies()
    print(f"Фильмов после фильтра: {len(movies)}")
    if movies.empty:
        print("Нет фильмов, подходящих под фильтр — сначала запусти src/collector.py")
        return

    directors = load_directors(set(movies["tconst"]))
    print(f"Фильмов с найденным режиссёром: {len(directors)}")

    docs = build_documents(movies, directors)
    load_to_mongo(docs)
    print(f"Загружено в MongoDB: {len(docs)} фильмов")


if __name__ == "__main__":
    run()
