"""
SupplyPulse — Construction de l'entrepot analytique DuckDB (donnees REELLES).

1. Charge le CSV DataCo Smart Supply Chain (data/dataco/) comme table brute.
2. Execute le modele de staging (pipeline/sql/staging/*.sql).
3. Materialise les marts (pipeline/sql/marts/*.sql).

DuckDB sert de moteur SQL analytique local : la syntaxe (DATE_TRUNC, strptime,
CTE, agregats conditionnels) est proche de BigQuery pour la portabilite cloud.

Usage : python pipeline/build_warehouse.py
"""

from __future__ import annotations

import glob
import os

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
SRC_CSV = os.path.join(ROOT, "data", "dataco", "dataco_supply_chain.csv")
DB_PATH = os.path.join(ROOT, "warehouse.duckdb")


def load_raw(con: duckdb.DuckDBPyConnection) -> None:
    print("[1/3] Chargement de la source DataCo...")
    if not os.path.exists(SRC_CSV):
        raise FileNotFoundError(
            f"{SRC_CSV} introuvable. Lance d'abord : python pipeline/download_data.py"
        )
    path = SRC_CSV.replace("\\", "/")
    con.execute(
        "CREATE OR REPLACE TABLE dataco_raw AS "
        f"SELECT * FROM read_csv_auto('{path}', sample_size=-1)"
    )
    n = con.execute("SELECT COUNT(*) FROM dataco_raw").fetchone()[0]
    c = len(con.execute("DESCRIBE dataco_raw").fetchall())
    print(f"      dataco_raw : {n:,} lignes x {c} colonnes")


def run_sql_dir(con: duckdb.DuckDBPyConnection, subdir: str, label: str) -> None:
    files = sorted(glob.glob(os.path.join(HERE, "sql", subdir, "*.sql")))
    print(f"{label} ({len(files)} fichiers)...")
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            con.execute(fh.read())
        print(f"      OK  {os.path.basename(f)}")


def summary(con: duckdb.DuckDBPyConnection) -> None:
    print("\nResume des objets construits :")
    for obj in [
        "fct_sales",
        "mart_monthly_performance",
        "mart_shipping_mode",
        "mart_category_finance",
        "mart_region",
    ]:
        n = con.execute(f"SELECT COUNT(*) FROM {obj}").fetchone()[0]
        print(f"      {obj:28s} {n:>8,} lignes")


def main() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = duckdb.connect(DB_PATH)
    try:
        load_raw(con)
        run_sql_dir(con, "staging", "[2/3] Staging")
        run_sql_dir(con, "marts", "[3/3] Marts")
        summary(con)
        print(f"\nEntrepot construit : {os.path.relpath(DB_PATH, ROOT)}")
    finally:
        con.close()


if __name__ == "__main__":
    main()
