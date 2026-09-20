# IMDb Movie Analytics

Аналитика по фильмам IMDb: тренды жанров по десятилетиям, рейтинг vs. число голосов, режиссёры и т.д. Данные — официальные [IMDb non-commercial datasets](https://datasets.imdbws.com/), хранение и визуализация — MongoDB Atlas + встроенный [MongoDB Charts](https://www.mongodb.com/products/charts).

## Архитектура

```
[datasets.imdbws.com] → collector.py → data/raw/*.tsv.gz → etl.py → MongoDB Atlas (movies) → MongoDB Charts
```

- **`src/collector.py`** — скачивает `title.basics`, `title.ratings`, `title.principals`, `name.basics` в `data/raw/`.
- **`src/etl.py`** — фильтрует фильмы по году и числу голосов (`MIN_YEAR`, `MIN_VOTES` в `.env` — полный IMDb слишком большой для бесплатного тира Atlas), достаёт режиссёров и загружает в коллекцию `movies`.
- **MongoDB Charts** — дашборды строятся прямо в Atlas UI поверх коллекции `movies`, без своего кода.
- **`.github/workflows/update_data.yml`** — еженедельное обновление данных через GitHub Actions (секрет `MONGODB_URI`).

## Установка и запуск

```bash
cp .env.example .env          # вставить свою connection string из MongoDB Atlas

pip install -r requirements.txt

python src/collector.py       # скачать дампы IMDb (несколько сотен MB, минуты)
python src/etl.py             # отфильтровать и загрузить фильмы в MongoDB
```

Дашборды строятся в Atlas: **Charts** в левом меню → **Add Dashboard** → источник данных — коллекция `movies`.

## Структура репозитория

```
imdbProject/
├── src/
│   ├── collector.py   # скачивание дампов IMDb
│   ├── db.py            # подключение к MongoDB Atlas
│   └── etl.py            # фильтрация и загрузка фильмов в Mongo
├── data/
│   ├── raw/                  # сырые дампы IMDb (не в git)
│   └── processed/            # (зарезервировано)
├── .github/workflows/
│   └── update_data.yml         # еженедельное обновление
├── .env.example
└── requirements.txt
```

## Модель данных (MongoDB)

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
  "directors": ["Имя режиссёра"]
}
```

## Стек

Python (requests, pandas, pymongo), MongoDB Atlas + MongoDB Charts, GitHub Actions.
