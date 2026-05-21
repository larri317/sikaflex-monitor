"""
Gestión de la base de datos de precios (CSV).
Guarda y consulta precios históricos por día, tienda y producto.
"""

import csv
import os
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from scraper import PriceResult

DATA_DIR = Path(__file__).parent.parent / "data"
PRICES_FILE = DATA_DIR / "prices.csv"
FIELDNAMES = ["date", "store", "product", "price", "url"]


def _ensure_file():
    DATA_DIR.mkdir(exist_ok=True)
    if not PRICES_FILE.exists():
        with open(PRICES_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def save_prices(results: list[PriceResult], run_date: Optional[date] = None):
    """Guarda los precios del día en el CSV. Si ya existe la entrada, la actualiza."""
    _ensure_file()
    today = (run_date or date.today()).isoformat()

    # Leer filas existentes
    existing = []
    with open(PRICES_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing.append(row)

    # Crear índice por (date, store, product) para upsert
    index = {(r["date"], r["store"], r["product"]): i for i, r in enumerate(existing)}

    for result in results:
        key = (today, result.store, result.product)
        new_row = {
            "date": today,
            "store": result.store,
            "product": result.product,
            "price": f"{result.price:.2f}",
            "url": result.url,
        }
        if key in index:
            existing[index[key]] = new_row   # actualizar
        else:
            existing.append(new_row)         # insertar

    with open(PRICES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(existing)

    print(f"💾 {len(results)} precios guardados para {today}")


def load_prices(product: Optional[str] = None, days_back: int = 30) -> list[dict]:
    """Carga precios históricos filtrados por producto y ventana de días."""
    _ensure_file()
    cutoff = (date.today() - timedelta(days=days_back)).isoformat()
    rows = []
    with open(PRICES_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["date"] < cutoff:
                continue
            if product and row["product"] != product:
                continue
            rows.append(row)
    return rows


def get_daily_average(product: str, target_date: Optional[date] = None) -> Optional[float]:
    """Calcula la media de precios de un producto en una fecha dada."""
    target = (target_date or date.today()).isoformat()
    rows = load_prices(product=product, days_back=60)
    prices = [float(r["price"]) for r in rows if r["date"] == target]
    if not prices:
        return None
    return round(statistics.mean(prices), 2)


def get_historical_average(product: str, days_back: int = 7) -> Optional[float]:
    """Media histórica de los últimos N días (excluyendo hoy)."""
    today = date.today().isoformat()
    rows = load_prices(product=product, days_back=days_back + 1)
    prices = [float(r["price"]) for r in rows if r["date"] < today]
    if not prices:
        return None
    return round(statistics.mean(prices), 2)


def get_store_yesterday_price(store: str, product: str) -> Optional[float]:
    """Último precio conocido de una tienda para un producto (antes de hoy)."""
    today = date.today().isoformat()
    rows = load_prices(product=product, days_back=30)
    # ordenar desc por fecha
    rows_store = sorted(
        [r for r in rows if r["store"] == store and r["date"] < today],
        key=lambda r: r["date"],
        reverse=True,
    )
    if rows_store:
        return float(rows_store[0]["price"])
    return None
