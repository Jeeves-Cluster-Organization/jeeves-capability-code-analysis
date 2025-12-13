"""Mock database client for testing.

Provides in-memory database operations for testing
without requiring a real PostgreSQL connection.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


class MockDatabaseClient:
    """Mock database client for testing.

    Provides in-memory storage for common database operations.
    """

    def __init__(self):
        self._tables: Dict[str, List[Dict[str, Any]]] = {}
        self._connected = False

    async def connect(self):
        """Mock connection."""
        self._connected = True

    async def disconnect(self):
        """Mock disconnection."""
        self._connected = False

    async def fetch_one(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single record."""
        records = await self.fetch_all(table, where)
        return records[0] if records else None

    async def fetch_all(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all matching records."""
        if table not in self._tables:
            return []

        records = self._tables[table]

        if where:
            records = [
                r for r in records
                if all(r.get(k) == v for k, v in where.items())
            ]

        if order_by:
            reverse = order_by.startswith("-")
            key = order_by.lstrip("-")
            records = sorted(records, key=lambda r: r.get(key, ""), reverse=reverse)

        if limit:
            records = records[:limit]

        return records

    async def insert(self, table: str, data: Dict[str, Any]) -> str:
        """Insert a record."""
        if table not in self._tables:
            self._tables[table] = []

        # Add timestamps if not present
        now = datetime.now(timezone.utc)
        if "created_at" not in data:
            data["created_at"] = now
        if "updated_at" not in data:
            data["updated_at"] = now

        # Generate ID if not present
        record_id = data.get("id") or f"mock-{table}-{len(self._tables[table])}"
        data["id"] = record_id

        self._tables[table].append(data)
        return record_id

    async def update(
        self,
        table: str,
        data: Dict[str, Any],
        where: Dict[str, Any],
    ) -> int:
        """Update matching records."""
        if table not in self._tables:
            return 0

        count = 0
        for record in self._tables[table]:
            if all(record.get(k) == v for k, v in where.items()):
                record.update(data)
                record["updated_at"] = datetime.now(timezone.utc)
                count += 1

        return count

    async def delete(self, table: str, where: Dict[str, Any]) -> int:
        """Delete matching records."""
        if table not in self._tables:
            return 0

        original_len = len(self._tables[table])
        self._tables[table] = [
            r for r in self._tables[table]
            if not all(r.get(k) == v for k, v in where.items())
        ]
        return original_len - len(self._tables[table])

    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None):
        """Execute raw SQL (no-op for mock)."""
        pass

    def reset(self):
        """Clear all data."""
        self._tables = {}

    def seed_data(self, table: str, records: List[Dict[str, Any]]):
        """Seed table with test data."""
        self._tables[table] = records
