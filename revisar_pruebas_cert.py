import sqlite3
from pathlib import Path

dbs = [
    Path("test_data/ecf/test_run_registry_cert.sqlite3"),
    Path("test_data/ecf/test_run_registry_cert_rfce.sqlite3"),
]

for db in dbs:
    print("\n" + "=" * 80)
    print(f"BASE DE DATOS: {db}")
    print("=" * 80)

    if not db.exists():
        print("NO EXISTE")
        continue

    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row

    for table in ("ecf_test_runs", "ecf_test_run_history"):
        exists = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        ).fetchone()

        if not exists:
            continue

        print(f"\n--- {table} ---")
        rows = con.execute(f'SELECT * FROM "{table}"').fetchall()
        print(f"Total de registros: {len(rows)}")

        for row in rows:
            data = dict(row)
            relevant = {
                k: v for k, v in data.items()
                if any(word in k.lower() for word in (
                    "case", "encf", "ncf", "status", "estado",
                    "track", "result", "message", "archived"
                ))
            }
            print(relevant if relevant else data)

    con.close()
