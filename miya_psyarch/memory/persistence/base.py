from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PersistenceWriteResult:
    ok: bool
    backend: str
    operation: str
    rows_written: int = 0
    error: str = ""


class MemoryPersistenceAdapter(Protocol):
    """
    Authoritative memory sink for AP snapshots.

    This adapter deliberately receives already-built white-box payloads instead
    of owning cognition itself. PostgreSQL is the durable truth layer; posting,
    ANN, numeric, relation and online-learning stores remain derived runtime
    views that can be rebuilt from these writes.
    """

    backend_name: str

    def write_snapshot(
        self,
        *,
        snapshot: dict,
        features: dict,
        vector: list[float],
        energy_profile: dict[str, float],
        energy_mass: float,
        numeric_features: dict[str, list[float]],
        relation_features: dict,
        previous_memory_id: str,
    ) -> PersistenceWriteResult:
        ...

    def summary(self) -> dict:
        ...


class NullMemoryPersistence:
    backend_name = "none"

    def write_snapshot(
        self,
        *,
        snapshot: dict,
        features: dict,
        vector: list[float],
        energy_profile: dict[str, float],
        energy_mass: float,
        numeric_features: dict[str, list[float]],
        relation_features: dict,
        previous_memory_id: str,
    ) -> PersistenceWriteResult:
        return PersistenceWriteResult(ok=True, backend=self.backend_name, operation="write_snapshot", rows_written=0)

    def summary(self) -> dict:
        return {
            "backend": self.backend_name,
            "enabled": False,
            "meaning": "runtime_only_memory;no_authoritative_persistence_attached",
        }

    def load_recent_snapshots(self, *, memory_kind: str | None = None, limit_per_kind: int = 128) -> list[dict]:
        return []

    def snapshot_by_id(self, memory_id: str) -> dict | None:
        return None
