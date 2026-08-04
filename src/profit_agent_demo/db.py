from collections.abc import Iterable
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import Settings


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings

    def fetch(self, query: str, params: Iterable[Any]) -> list[dict[str, Any]]:
        with psycopg.connect(
            host=self.settings.pg_host,
            port=self.settings.pg_port,
            dbname=self.settings.pg_database,
            user=self.settings.pg_user,
            password=self.settings.pg_password,
            row_factory=dict_row,
            options="-c statement_timeout=30000 -c default_transaction_read_only=on",
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, list(params))
                return [dict(row) for row in cursor.fetchall()]
