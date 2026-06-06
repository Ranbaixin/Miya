from __future__ import annotations

from .base import PersistenceWriteResult


class RecordingMemoryPersistence:
    """
    In-process test adapter for the PostgreSQL persistence contract.

    It records the exact payload shape MemoryStore sends to the authoritative
    layer without pretending to be a database. This keeps unit tests fast while
    preserving the AP boundary: cognition writes durable evidence; derived
    runtime indexes remain separate.
    """

    backend_name = "recording"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = bool(fail)
        self.writes: list[dict] = []
        self.errors: list[str] = []

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
        if self.fail:
            error = "recording_adapter_forced_failure"
            self.errors.append(error)
            return PersistenceWriteResult(ok=False, backend=self.backend_name, operation="write_snapshot", rows_written=0, error=error)
        payload = {
            "snapshot": dict(snapshot or {}),
            "features": dict(features or {}),
            "vector": list(vector or []),
            "energy_profile": dict(energy_profile or {}),
            "energy_mass": float(energy_mass or 0.0),
            "numeric_features": {str(key): list(value or []) for key, value in dict(numeric_features or {}).items()},
            "relation_features": dict(relation_features or {}),
            "previous_memory_id": str(previous_memory_id or ""),
        }
        self.writes.append(payload)
        rows = 1 + len(payload["snapshot"].get("items", []) or []) + len(payload["features"].get("labels", []) or [])
        return PersistenceWriteResult(ok=True, backend=self.backend_name, operation="write_snapshot", rows_written=rows)

    def summary(self) -> dict:
        return {
            "backend": self.backend_name,
            "enabled": True,
            "write_count": len(self.writes),
            "error_count": len(self.errors),
            "last_memory_id": str((self.writes[-1]["snapshot"] if self.writes else {}).get("memory_id", "") or ""),
        }

    def load_recent_snapshots(self, *, memory_kind: str | None = None, limit_per_kind: int = 128) -> list[dict]:
        cap = max(1, int(limit_per_kind))
        grouped: dict[str, list[dict]] = {}
        for write in self.writes:
            snapshot = dict(write.get("snapshot", {}) or {})
            kind = str(snapshot.get("memory_kind", "") or "")
            if memory_kind is not None and kind != str(memory_kind or ""):
                continue
            grouped.setdefault(kind, []).append(snapshot)
        rows: list[dict] = []
        for kind, snapshots in sorted(grouped.items()):
            ordered = sorted(snapshots, key=lambda row: int(row.get("tick_index", -1) or -1))
            rows.extend(ordered[-cap:])
        rows.sort(key=lambda row: (str(row.get("memory_kind", "") or ""), int(row.get("tick_index", -1) or -1), str(row.get("memory_id", "") or "")))
        return rows

    def snapshot_by_id(self, memory_id: str) -> dict | None:
        clean = str(memory_id or "")
        if not clean:
            return None
        for write in reversed(self.writes):
            snapshot = dict(write.get("snapshot", {}) or {})
            if str(snapshot.get("memory_id", "") or "") == clean:
                return snapshot
        return None
