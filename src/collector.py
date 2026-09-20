"""Download official IMDb non-commercial dataset dumps into data/raw/."""

import sys
from pathlib import Path

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "https://datasets.imdbws.com"
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Files needed to build the analytical movies collection.
FILES = [
    "title.basics.tsv.gz",  # title type, year, genres
    "title.ratings.tsv.gz",  # rating and vote count — filter for "notable" movies
    "title.principals.tsv.gz",  # title -> people link (actors, directors, ...)
    "name.basics.tsv.gz",  # people's names
    "title.akas.tsv.gz",  # regional titles — source for the markets field
]


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=30))
def _download(filename: str) -> Path:
    out_path = RAW_DIR / filename
    with requests.get(f"{BASE_URL}/{filename}", stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        written = 0
        with out_path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                written += len(chunk)
                if total:
                    print(
                        f"  {filename}: {written / 1e6:.0f}/{total / 1e6:.0f} MB",
                        end="\r",
                    )
    print(f"  {filename}: done ({written / 1e6:.0f} MB)")
    return out_path


def collect() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        print(f"Downloading {filename}...")
        _download(filename)


if __name__ == "__main__":
    collect()
