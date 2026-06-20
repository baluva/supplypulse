"""
SupplyPulse — Moteur de tests qualite (data governance).

Lit le dictionnaire de donnees (governance/data_dictionary.yml) et execute les
tests declares sur l'entrepot DuckDB : not_null, unique, positive,
accepted_values, accepted_range, relationships (integrite referentielle).

Produit :
  - un rapport console lisible ;
  - governance/quality_report.json consomme par le dashboard.

Usage : python governance/quality_checks.py
Code de sortie 1 si au moins un test echoue (utilisable en CI/CD).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import duckdb
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DB_PATH = os.path.join(ROOT, "warehouse.duckdb")
DICT_PATH = os.path.join(HERE, "data_dictionary.yml")
REPORT_PATH = os.path.join(HERE, "quality_report.json")


def scalar(con, sql: str) -> int:
    return con.execute(sql).fetchone()[0]


def run_test(con, table: str, column: str, spec) -> dict:
    """Execute un test unitaire et renvoie un dict de resultat normalise."""
    # Un test est soit une chaine simple ('not_null'), soit un dict a une cle.
    if isinstance(spec, str):
        name, cfg = spec, {}
    else:
        name, cfg = next(iter(spec.items()))

    failing = 0
    detail = ""

    if name == "not_null":
        failing = scalar(con, f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL")
    elif name == "unique":
        failing = scalar(
            con,
            f"SELECT COALESCE(SUM(c - 1), 0) FROM "
            f"(SELECT COUNT(*) c FROM {table} GROUP BY {column} HAVING COUNT(*) > 1)",
        )
    elif name == "positive":
        failing = scalar(con, f"SELECT COUNT(*) FROM {table} WHERE {column} <= 0")
    elif name == "accepted_values":
        vals = cfg["values"]
        in_list = ", ".join("'" + str(v).replace("'", "''") + "'" for v in vals)
        failing = scalar(
            con,
            f"SELECT COUNT(*) FROM {table} "
            f"WHERE {column} IS NOT NULL AND {column} NOT IN ({in_list})",
        )
        detail = f"domaine autorise : {vals}"
    elif name == "accepted_range":
        conds = []
        if "min" in cfg:
            conds.append(f"{column} < {cfg['min']}")
        if "max" in cfg:
            conds.append(f"{column} > {cfg['max']}")
        where = " OR ".join(conds) if conds else "FALSE"
        failing = scalar(con, f"SELECT COUNT(*) FROM {table} WHERE {where}")
        detail = f"bornes : {cfg}"
    elif name == "relationships":
        ref_table, ref_field = cfg["to"], cfg["field"]
        failing = scalar(
            con,
            f"SELECT COUNT(*) FROM {table} t "
            f"WHERE t.{column} IS NOT NULL AND t.{column} NOT IN "
            f"(SELECT {ref_field} FROM {ref_table})",
        )
        detail = f"-> {ref_table}.{ref_field}"
    else:
        return {
            "table": table, "column": column, "test": name,
            "status": "SKIP", "failing_rows": 0, "detail": "test inconnu",
        }

    return {
        "table": table,
        "column": column,
        "test": name,
        "status": "PASS" if failing == 0 else "FAIL",
        "failing_rows": int(failing),
        "detail": detail,
    }


def main() -> None:
    if not os.path.exists(DB_PATH):
        sys.exit("Entrepot introuvable. Lance d'abord : python pipeline/build_warehouse.py")

    with open(DICT_PATH, "r", encoding="utf-8") as fh:
        catalog = yaml.safe_load(fh)

    con = duckdb.connect(DB_PATH, read_only=True)
    results = []
    for table in catalog["tables"]:
        tname = table["name"]
        for col in table.get("columns", []):
            for spec in col.get("tests", []):
                results.append(run_test(con, tname, col["name"], spec))
    con.close()

    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]

    # --- Rapport console ----------------------------------------------------
    print("=" * 68)
    print("  SupplyPulse — Rapport qualite des donnees")
    print("=" * 68)
    for r in results:
        if r["status"] == "FAIL":
            mark = "[FAIL]"
        elif r["status"] == "PASS":
            mark = "[ OK ]"
        else:
            mark = "[SKIP]"
        line = f"{mark} {r['table']}.{r['column']} :: {r['test']}"
        if r["status"] == "FAIL":
            line += f"  ({r['failing_rows']} lignes en defaut)"
        print(line)

    total = len(results)
    score = round(100.0 * len(passed) / total, 1) if total else 0.0
    print("-" * 68)
    print(f"  Tests : {total} | Reussis : {len(passed)} | Echecs : {len(failed)} "
          f"| Score qualite : {score}%")
    print("=" * 68)

    # --- Rapport JSON pour le dashboard -------------------------------------
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_tests": total,
        "passed": len(passed),
        "failed": len(failed),
        "quality_score": score,
        "results": results,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(f"Rapport ecrit : {os.path.relpath(REPORT_PATH, ROOT)}")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
