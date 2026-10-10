"""Persistent SQLite registry for DGII e-CF certification test submissions.

The registry fails closed: an e-NCF already present in the database cannot be
reserved for another send. Network timeouts should be reconciled with DGII
before an operator manually changes any record.
"""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FINAL_OR_SUBMITTED_STATUSES = {
    "sending",
    "submitted",
    "processing",
    "accepted",
    "accepted_conditional",
    "rejected",
    "unknown",
}


class RegistryError(RuntimeError):
    """Base error for registry operations."""


class DuplicateECFError(RegistryError):
    """Raised when an e-NCF is already reserved or recorded."""


@dataclass(frozen=True)
class RegistryRecord:
    rnc: str
    encf: str
    case_id: str | None
    tipo_ecf: str | None
    status: str
    xml_sha256: str | None
    track_id: str | None
    dgii_code: int | None
    dgii_status: str | None
    sequence_used: bool | None
    sent_at: str | None
    result_at: str | None
    notes: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ECFTestRegistry:
    def __init__(self, db_path: str | Path = "test_data/ecf/test_run_registry.sqlite3"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS ecf_test_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rnc TEXT NOT NULL,
                    encf TEXT NOT NULL,
                    case_id TEXT,
                    tipo_ecf TEXT,
                    status TEXT NOT NULL,
                    xml_sha256 TEXT,
                    track_id TEXT UNIQUE,
                    dgii_code INTEGER,
                    dgii_status TEXT,
                    sequence_used INTEGER,
                    sent_at TEXT,
                    result_at TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (rnc, encf)
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS ix_ecf_test_runs_case_id
                ON ecf_test_runs(case_id)
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS ix_ecf_test_runs_status
                ON ecf_test_runs(status)
            """)

    def get(self, rnc: str, encf: str) -> RegistryRecord | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM ecf_test_runs WHERE rnc = ? AND encf = ?",
                (rnc, encf),
            ).fetchone()
        return self._to_record(row) if row else None

    def reserve_send(
        self,
        *,
        rnc: str,
        encf: str,
        case_id: str | None,
        tipo_ecf: str | None,
        signed_xml: bytes,
        notes: str | None = None,
    ) -> RegistryRecord:
        """Atomically reserve an e-NCF immediately before its first network send.

        Any existing row blocks a second send, including prior failed/conditional
        results. This intentionally prioritizes preventing duplicate submissions.
        """
        now = utc_now()
        digest = sha256_hex(signed_xml)
        try:
            with self._connect() as db:
                db.execute(
                    """
                    INSERT INTO ecf_test_runs
                    (rnc, encf, case_id, tipo_ecf, status, xml_sha256,
                     notes, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'sending', ?, ?, ?, ?)
                    """,
                    (rnc, encf, case_id, tipo_ecf, digest, notes, now, now),
                )
                row = db.execute(
                    "SELECT * FROM ecf_test_runs WHERE rnc = ? AND encf = ?",
                    (rnc, encf),
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            existing = self.get(rnc, encf)
            detail = (
                f"e-NCF {encf} del RNC {rnc} ya está registrado "
                f"con estado '{existing.status}'"
                if existing else f"e-NCF {encf} del RNC {rnc} ya está registrado"
            )
            raise DuplicateECFError(
                detail + ". No se enviará nuevamente automáticamente."
            ) from exc
        return self._to_record(row)

    def mark_submitted(
        self,
        *,
        rnc: str,
        encf: str,
        track_id: str,
        notes: str | None = None,
    ) -> RegistryRecord:
        now = utc_now()
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE ecf_test_runs
                SET status = 'submitted',
                    track_id = ?,
                    sent_at = COALESCE(sent_at, ?),
                    notes = COALESCE(?, notes),
                    updated_at = ?
                WHERE rnc = ? AND encf = ? AND status = 'sending'
                """,
                (track_id, now, notes, now, rnc, encf),
            )
            if cursor.rowcount != 1:
                raise RegistryError(
                    f"No se pudo registrar TrackId para {rnc}/{encf}; "
                    "no existe una reserva en estado 'sending'."
                )
            row = db.execute(
                "SELECT * FROM ecf_test_runs WHERE rnc = ? AND encf = ?",
                (rnc, encf),
            ).fetchone()
        return self._to_record(row)

    def mark_result(
        self,
        *,
        rnc: str,
        encf: str,
        code: int | None,
        status: str | None,
        sequence_used: bool | None,
        notes: str | None = None,
    ) -> RegistryRecord:
        normalized = {
            1: "accepted",
            2: "rejected",
            3: "processing",
            4: "accepted_conditional",
        }.get(code, "unknown")
        now = utc_now()
        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE ecf_test_runs
                SET status = ?,
                    dgii_code = ?,
                    dgii_status = ?,
                    sequence_used = ?,
                    result_at = ?,
                    notes = COALESCE(?, notes),
                    updated_at = ?
                WHERE rnc = ? AND encf = ?
                """,
                (
                    normalized,
                    code,
                    status,
                    None if sequence_used is None else int(sequence_used),
                    now,
                    notes,
                    now,
                    rnc,
                    encf,
                ),
            )
            if cursor.rowcount != 1:
                raise RegistryError(
                    f"No existe un registro para {rnc}/{encf}; "
                    "no se puede asociar el resultado."
                )
            row = db.execute(
                "SELECT * FROM ecf_test_runs WHERE rnc = ? AND encf = ?",
                (rnc, encf),
            ).fetchone()
        return self._to_record(row)

    def record_historical(
        self,
        *,
        rnc: str,
        encf: str,
        case_id: str,
        tipo_ecf: str,
        status: str,
        dgii_code: int | None,
        dgii_status: str,
        track_id: str | None = None,
        sequence_used: bool | None = None,
        notes: str | None = None,
    ) -> RegistryRecord:
        """Import a known past outcome without pretending to know its XML hash."""
        normalized = status.strip().lower().replace(" ", "_")
        allowed = {
            "accepted", "accepted_conditional", "rejected",
            "processing", "submitted", "unknown", "sending"
        }
        if normalized not in allowed:
            raise ValueError(f"Estado histórico no permitido: {status}")

        now = utc_now()
        with self._connect() as db:
            existing = db.execute(
                "SELECT * FROM ecf_test_runs WHERE rnc = ? AND encf = ?",
                (rnc, encf),
            ).fetchone()
            if existing:
                # Never downgrade or overwrite an existing actual XML hash.
                updates = {
                    "case_id": existing["case_id"] or case_id,
                    "tipo_ecf": existing["tipo_ecf"] or tipo_ecf,
                    "track_id": existing["track_id"] or track_id,
                    "dgii_code": existing["dgii_code"] if existing["dgii_code"] is not None else dgii_code,
                    "dgii_status": existing["dgii_status"] or dgii_status,
                    "sequence_used": existing["sequence_used"] if existing["sequence_used"] is not None else (None if sequence_used is None else int(sequence_used)),
                    "status": existing["status"] if existing["xml_sha256"] else normalized,
                    "result_at": existing["result_at"] or now,
                    "notes": existing["notes"] or notes,
                    "updated_at": now,
                }
                db.execute(
                    """
                    UPDATE ecf_test_runs
                    SET case_id=:case_id, tipo_ecf=:tipo_ecf, track_id=:track_id,
                        dgii_code=:dgii_code, dgii_status=:dgii_status,
                        sequence_used=:sequence_used, status=:status,
                        result_at=:result_at, notes=:notes, updated_at=:updated_at
                    WHERE rnc=:rnc AND encf=:encf
                    """,
                    {**updates, "rnc": rnc, "encf": encf},
                )
            else:
                db.execute(
                    """
                    INSERT INTO ecf_test_runs
                    (rnc, encf, case_id, tipo_ecf, status, track_id, dgii_code,
                     dgii_status, sequence_used, sent_at, result_at, notes,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rnc, encf, case_id, tipo_ecf, normalized, track_id,
                        dgii_code, dgii_status,
                        None if sequence_used is None else int(sequence_used),
                        now if track_id else None, now, notes, now, now,
                    ),
                )
            row = db.execute(
                "SELECT * FROM ecf_test_runs WHERE rnc = ? AND encf = ?",
                (rnc, encf),
            ).fetchone()
        return self._to_record(row)

    def list_records(self) -> list[RegistryRecord]:
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT * FROM ecf_test_runs
                ORDER BY CASE WHEN case_id IS NULL THEN 1 ELSE 0 END,
                         case_id, encf
                """
            ).fetchall()
        return [self._to_record(row) for row in rows]

    @staticmethod
    def _to_record(row: sqlite3.Row) -> RegistryRecord:
        return RegistryRecord(
            rnc=row["rnc"],
            encf=row["encf"],
            case_id=row["case_id"],
            tipo_ecf=row["tipo_ecf"],
            status=row["status"],
            xml_sha256=row["xml_sha256"],
            track_id=row["track_id"],
            dgii_code=row["dgii_code"],
            dgii_status=row["dgii_status"],
            sequence_used=None if row["sequence_used"] is None else bool(row["sequence_used"]),
            sent_at=row["sent_at"],
            result_at=row["result_at"],
            notes=row["notes"],
        )
