"""
config/database.py
ClickHouse connection management following SOLID principles.
Single Responsibility: only handles DB connectivity.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

import clickhouse_connect
from clickhouse_connect.driver import Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ClickHouseConfig:
    """Value object holding connection parameters."""

    def __init__(self) -> None:
        self.host: str = os.getenv("CH_HOST", "")
        self.port: int = int(os.getenv("CH_PORT", ""))
        self.username: str = os.getenv("CH_USERNAME", "")
        self.password: str = os.getenv("CH_PASSWORD", "")

    def __repr__(self) -> str:
        return f"ClickHouseConfig(host={self.host}, port={self.port}, user={self.username})"


class ClickHouseConnection:
    """
    Manages a lazy singleton ClickHouse client.
    Open/Closed: extend by subclassing, no modification needed.
    """

    _client: Optional[Client] = None

    def __init__(self, config: Optional[ClickHouseConfig] = None) -> None:
        self._config = config or ClickHouseConfig()

    def get_client(self) -> Client:
        if self._client is None:
            self._client = self._create_client()
        return self._client

    def _create_client(self) -> Client:
        try:
            client = clickhouse_connect.get_client(
                host=self._config.host,
                port=self._config.port,
                username=self._config.username,
                password=self._config.password,
                connect_timeout=10,
                query_retries=2,
            )
            logger.info("ClickHouse connection established: %s", self._config)
            return client
        except Exception as exc:
            logger.error("ClickHouse connection failed: %s", exc)
            raise

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
