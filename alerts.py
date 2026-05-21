"""
Motor de detección de alertas de precios.
Detecta cuando una tienda sube el precio más de un umbral respecto a la media.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional
import logging

from scraper import PriceResult
from database import get_historical_average, get_store_yesterday_price

logger = logging.getLogger(__name__)

ALERT_THRESHOLD = 0.10   # 10% de subida dispara la alerta
PRODUCTS = ["522", "621"]


@dataclass
class PriceAlert:
    store: str
    product: str
    url: str
    current_price: float
    reference_price: float      # media histórica o precio anterior
    reference_type: str         # "media 7 días" o "precio anterior"
    pct_change: float           # positivo = subida, negativo = bajada
    alert_type: str             # "SUBIDA >10%" | "BAJADA >10%"

    @property
    def emoji(self) -> str:
        return "🔴" if self.pct_change > 0 else "🟢"

    @property
    def summary(self) -> str:
        direction = "subida" if self.pct_change > 0 else "bajada"
        return (
            f"{self.emoji} {self.store} | Sikaflex {self.product} | "
            f"{self.reference_price:.2f}€ → {self.current_price:.2f}€ "
            f"({self.pct_change:+.1f}% {direction} vs {self.reference_type})"
        )


def detect_alerts(
    results: list[PriceResult],
    threshold: float = ALERT_THRESHOLD,
) -> list[PriceAlert]:
    """
    Analiza los precios del día y devuelve alertas para cualquier tienda
    cuyo precio haya variado más de `threshold` respecto a:
      1. Su propio precio del día anterior (si existe)
      2. La media histórica de 7 días del producto
    """
    alerts = []

    for result in results:
        # ── Referencia 1: precio anterior de esa tienda ──────────
        prev_price = get_store_yesterday_price(result.store, result.product)
        if prev_price:
            pct = (result.price - prev_price) / prev_price
            if abs(pct) > threshold:
                alerts.append(PriceAlert(
                    store=result.store,
                    product=result.product,
                    url=result.url,
                    current_price=result.price,
                    reference_price=prev_price,
                    reference_type="precio anterior",
                    pct_change=round(pct * 100, 2),
                    alert_type="SUBIDA >10%" if pct > 0 else "BAJADA >10%",
                ))
            continue   # si ya tenemos histórico de esa tienda, usarlo es más preciso

        # ── Referencia 2: media histórica del producto (7 días) ──
        avg = get_historical_average(result.product, days_back=7)
        if avg:
            pct = (result.price - avg) / avg
            if abs(pct) > threshold:
                alerts.append(PriceAlert(
                    store=result.store,
                    product=result.product,
                    url=result.url,
                    current_price=result.price,
                    reference_price=avg,
                    reference_type="media 7 días",
                    pct_change=round(pct * 100, 2),
                    alert_type="SUBIDA >10%" if pct > 0 else "BAJADA >10%",
                ))
        else:
            logger.info(
                f"ℹ️  {result.store} [{result.product}] — primer registro, sin histórico para comparar."
            )

    return alerts


def build_daily_summary(
    results: list[PriceResult],
    alerts: list[PriceAlert],
    today: Optional[date] = None,
) -> dict:
    """Construye el resumen diario completo para el email."""
    today = today or date.today()

    # Media del día por producto
    daily_avgs = {}
    for product in PRODUCTS:
        prices = [r.price for r in results if r.product == product]
        daily_avgs[product] = round(sum(prices) / len(prices), 2) if prices else None

    # Media histórica (7 días) por producto
    hist_avgs = {}
    for product in PRODUCTS:
        hist_avgs[product] = get_historical_average(product, days_back=7)

    return {
        "date": today.isoformat(),
        "results": results,
        "alerts": alerts,
        "daily_averages": daily_avgs,
        "historical_averages": hist_avgs,
        "stores_scraped": len(results),
        "alerts_count": len(alerts),
    }
