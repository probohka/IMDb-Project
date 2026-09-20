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

- **`src/collector.py`** — downloads `title.basics`, `title.ratings`, `title.principals`, `name.basics`, `title.akas` into `data/raw/`.
- **`src/etl.py`** — filters movies by year and vote count (`MIN_YEAR`, `MIN_VOTES` — the full IMDb dataset is too large for Atlas's free tier), resolves directors, derives localization markets, and loads everything into the `movies` collection.
- **MongoDB Charts** — dashboards are built directly in the Atlas UI on top of the `movies` collection, no custom code required.
- **`.github/workflows/update_data.yml`** — weekly data refresh via GitHub Actions (uses the `MONGODB_URI` secret).

### Local vs. cloud runs

The pipeline can run in two places, and each reads its config from a different, independent source:

- **Locally** — `collector.py`/`etl.py` read `.env` (via `python-dotenv`) for `MONGODB_URI`, `DB_NAME`, `MIN_YEAR`, `MIN_VOTES`. Useful for one-off exploration of raw data or testing filter changes without touching the scheduled pipeline.
- **In the cloud** — `.github/workflows/update_data.yml` runs the same two scripts on a GitHub-hosted runner. `.env` is gitignored and never reaches the runner, so the workflow sets `MONGODB_URI` (from the `MONGODB_URI` repository secret), `MIN_YEAR`, and `MIN_VOTES` directly in its own `env:` block.

These two configs don't sync automatically — changing a filter value in `.env` has no effect on the cloud run, and vice versa. Update both when adjusting `MIN_YEAR`/`MIN_VOTES`.

### MongoDB Atlas network access

GitHub-hosted Actions runners are ephemeral VMs drawn from a large, dynamically allocated IP pool that changes between (and sometimes during) runs — there's no single fixed IP that can be safely whitelisted ahead of time. Atlas's **Network Access** list therefore needs `0.0.0.0/0` (Allow Access from Anywhere) for the workflow to connect at all; access control is enforced by the database user's credentials rather than by source IP, which is the standard model for CI/CD integrations connecting to a managed database.

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
  "directors": ["Director name"],
  "markets": ["US", "CA", "GB"]
}
```

`markets` is derived from `title.akas` (regions where IMDb shows the title as its display title, `type=imdbDisplay`) — it approximates localization/distribution reach, not an official country of production or real box-office release data (IMDb's free datasets don't include either).

## Known limitations

- **Non-atomic collection reload**: `etl.py` refreshes `movies` via `delete_many({})` followed by `insert_many(...)`, so there's a brief window where the collection is empty. For a weekly personal-project refresh this is harmless (the gap lasts seconds), but if someone hits the Atlas Charts dashboard during that window, they'll see 0 movies. A zero-downtime production setup would instead load into a temporary collection and atomically swap it in with `renameCollection`, so readers never see an empty state.

## Stack

Python (requests, pandas, pymongo), MongoDB Atlas + MongoDB Charts, GitHub Actions.
