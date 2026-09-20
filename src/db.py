"""Подключение к MongoDB Atlas: общий клиент для ETL."""

import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
DB_NAME = os.environ.get("DB_NAME", "imdb_graph")


def get_db() -> Database:
    client = MongoClient(MONGODB_URI)
    return client[DB_NAME]
