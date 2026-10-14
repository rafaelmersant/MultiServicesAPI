import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

db = Path("test_data/ecf/test_run_registry_cert_rfce.sqlite3")
backup = db.with_name(
    f"{db.stem}_backup_{datetime.now():%Y%m%d_%H%M%S}{db.suffix}"
)

if not db.exists():
    raise SystemExit(f"No existe la base de datos: {db}")

shutil.copy2(db, backup)
print(f"Respaldo creado: {backup}")

con = sqlite3.connect(db)
try:
    con.execute("BEGIN IMMEDIATE")

    tables = {
        row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    if not {"ecf_test_runs", "ecf_test_run_history"}.issubset(tables):
        raise RuntimeError(
            f"No se encontraron las tablas esperadas. Tablas: {sorted(tables)}"
        )

    active_cols = {
        row[1] for row in con.execute("PRAGMA table_info(ecf_test_runs)")
    }
    history_info = list(
        con.execute("PRAGMA table_info(ecf_test_run_history)")
    )
    history_cols = {row[1] for row in history_info}

    common = [
        row[1] for row in history_info
        if row[1] in active_cols and row[1] != "id"
    ]

    if not common:
        raise RuntimeError("No hay columnas compatibles para archivar.")

    cols = ", ".join(f'"{c}"' for c in common)
    con.execute(
        f"INSERT INTO ecf_test_run_history ({cols}) "
        f"SELECT {cols} FROM ecf_test_runs"
    )

    archived = con.execute("SELECT changes()").fetchone()[0]
    con.execute("DELETE FROM ecf_test_runs")
    con.commit()

    print(f"Registros archivados: {archived}")
    print("Registro activo de RFCE limpiado correctamente.")
except Exception:
    con.rollback()
    raise
finally:
    con.close()
