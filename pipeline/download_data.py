"""
SupplyPulse — Telechargement de la source de donnees REELLE.

Jeu de donnees : "DataCo Smart Supply Chain" (180 519 lignes, 53 variables,
commandes reelles 2015-2018 : ventes, profit, logistique, dates d'expedition
reelles vs planifiees, statut de livraison, mode de transport, marche mondial).

Source d'origine : Mendeley Data (Constante & al.) / Kaggle.
Mirror telecharge ici (sans authentification) :
  github.com/ashishpatel26/DataCo-SMART-SUPPLY-CHAIN-FOR-BIG-DATA-ANALYSIS

Le fichier source est encode en latin-1 (noms produits espagnols) : on le
convertit une fois en UTF-8 pour la portabilite du pipeline.

Usage : python pipeline/download_data.py
"""

from __future__ import annotations

import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
DATA_DIR = os.path.join(ROOT, "data", "dataco")

BASE = ("https://raw.githubusercontent.com/ashishpatel26/"
        "DataCo-SMART-SUPPLY-CHAIN-FOR-BIG-DATA-ANALYSIS/main")
DATASET_URL = f"{BASE}/DataCoSupplyChainDataset.csv"
DESC_URL = f"{BASE}/DescriptionDataCoSupplyChain.csv"

OUT_CSV = os.path.join(DATA_DIR, "dataco_supply_chain.csv")
OUT_DESC = os.path.join(DATA_DIR, "DescriptionDataCoSupplyChain.csv")


def download(url: str, dest: str) -> None:
    print(f"  -> {url}")
    urllib.request.urlretrieve(url, dest)
    print(f"     {os.path.getsize(dest) / 1e6:.1f} MB -> {os.path.relpath(dest, ROOT)}")


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = os.path.join(DATA_DIR, "_raw_latin1.csv")

    print("Telechargement du dictionnaire de colonnes...")
    download(DESC_URL, OUT_DESC)

    print("Telechargement du dataset (~95 MB)...")
    download(DATASET_URL, tmp)

    print("Conversion latin-1 -> UTF-8...")
    with open(tmp, "r", encoding="latin-1") as fin, \
         open(OUT_CSV, "w", encoding="utf-8", newline="") as fout:
        for line in fin:
            fout.write(line)
    os.remove(tmp)
    print(f"     UTF-8 pret -> {os.path.relpath(OUT_CSV, ROOT)}")
    print("\nTermine. Lance ensuite : python pipeline/build_warehouse.py")


if __name__ == "__main__":
    main()
