# IMDb Movie Analytics

<p align="center">
  <a href="https://www.imdb.com/">
    <img src="https://upload.wikimedia.org/wikipedia/commons/6/69/IMDB_Logo_2016.svg" alt="IMDb logo" width="200">
  </a>
</p>

Movie analytics built on [IMDb](https://www.imdb.com/) data: genre trends by decade, rating vs. vote count, directors, and more. Data comes from the official [IMDb non-commercial datasets](https://datasets.imdbws.com/); storage and visualization run on MongoDB Atlas with built-in [MongoDB Charts](https://www.mongodb.com/products/charts).

## Architecture

```
[datasets.imdbws.com] → collector.py → data/raw/*.tsv.gz → etl.py → MongoDB Atlas (movies) → MongoDB Charts
```

- **`src/collector.py`** — downloads `title.basics`, `title.ratings`, `title.principals`, `name.basics` into `data/raw/`.
- **`src/etl.py`** — filters movies by year and vote count (`MIN_YEAR`, `MIN_VOTES` in `.env` — the full IMDb dataset is too large for Atlas's free tier), resolves directors, and loads everything into the `movies` collection.
- **MongoDB Charts** — dashboards are built directly in the Atlas UI on top of the `movies` collection, no custom code required.
- **`.github/workflows/update_data.yml`** — weekly data refresh via GitHub Actions (uses the `MONGODB_URI` secret).

## Setup and usage

```bash
cp .env.example .env          # paste your MongoDB Atlas connection string

pip install -r requirements.txt

python src/collector.py       # download IMDb dumps (a few hundred MB, takes minutes)
python src/etl.py             # filter and load movies into MongoDB
```

Dashboards are built in Atlas: **Charts** in the left sidebar → **Add Dashboard** → data source is the `movies` collection.

## Repository structure

```
imdbProject/
├── src/
│   ├── collector.py   # downloads IMDb dumps
│   ├── db.py            # MongoDB Atlas connection
│   └── etl.py            # filters and loads movies into Mongo
├── data/
│   ├── raw/                  # raw IMDb dumps (not in git)
│   └── processed/            # (reserved)
├── .github/workflows/
│   └── update_data.yml         # weekly refresh
├── .env.example
└── requirements.txt
```

## Data model (MongoDB)

**`movies`**:
```json
{
  "_id": "tconst",
  "title": "string",
  "year": 2015,
  "decade": 2010,
  "genres": ["Action", "Drama"],
  "runtimeMinutes": 120,
  "rating": 7.8,
  "numVotes": 15234,
  "directors": ["Director name"]
}
```

## Stack

Python (requests, pandas, pymongo), MongoDB Atlas + MongoDB Charts, GitHub Actions.
