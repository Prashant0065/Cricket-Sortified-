import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "cricbuzz_livestats"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "connect_timeout": 5,
}


def get_connection():
    if not DB_CONFIG["password"]:
        raise RuntimeError("DB_PASSWORD is missing from the .env file.")

    return psycopg.connect(**DB_CONFIG)


def test_connection():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user, version();")
            return cur.fetchone()
