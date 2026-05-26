"""
Motor de detección de alertas de precios.
Cubre productos Sika y competencia.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional
import logging

from scraper import PriceResult
from database import get_historical_average, get_store_yesterday_price

logger = logging.getLogger(__name__)

ALERT_THRESHOLD = 0.10

# Todos los productos monitorizados
SIKA_PRODUCTS        = ["522", "554", "621"]
COMPETENCIA_PRODUCTS = ["T930", "T939", "SF45", "SS240", "QT"]
ALL_PRODUCTS         = SIKA_PRODUCTS + COMPETENCIA_PRODUCTS

PRODUCT_NAMES = {
    "522":  "Sikaflex® 522",
    "554":  "Sikaflex® 554",
    "621":  "Sikaflex® 621 Purform",
    "T930": "Teroson MS 930",
    "T939": "Teroson MS 939",
    "SF45": "Soudaflex 45 FC",
    "SS240":"Soudaseal 240 FC",
    "QT":   "Quiadsa Turbo",
}

PRODUCT_BRANDS = {
    "522": "Sika", "554": "Sika", "621": "Sika",
    "T930": "Teroson", "T939": "Teroson",
    "SF45": "Soudal", "SS240": "Soudal",
    "QT": "Quiadsa",
}


@dataclass
class PriceAlert:
    store: str
    product: str
    url: str
    current_price: float
    reference_price: float
    reference_type: str
    pct_change: float
    alert_type: str

    @property
    def emoji(self) -> str:
        return "🔴" if self.pct_change > 0 else "🟢"

    @property
    def summary(self) -> str:
        name = PRODUCT_NAMES.get(self.product, self.product)
        direction = "subida" if self.pct_change > 0 else "bajada"
        return (
            f"{self.emoji} {self.store} | {name} | "
            f"{self.reference_price:.2f}€ → {self.current_price:.2f}€ "
            f"({self.pct_change:+.1f}% {direction} vs {self.reference_type})"
        )


def detect_alerts(
    results: list[PriceResult],
    threshold: float = ALERT_THRESHOLD,
) -> list[PriceAlert]:
    alerts = []
    for result in results:
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
            continue

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
            logger.info(f"ℹ️  {result.store} [{result.product}] — primer registro.")

    return alerts


def build_daily_summary(
    results: list[PriceResult],
    alerts: list[PriceAlert],
    today: Optional[date] = None,
) -> dict:
    today = today or date.today()

    daily_avgs = {}
    for product in ALL_PRODUCTS:
        prices = [r.price for r in results if r.product == product]
        daily_avgs[product] = round(sum(prices) / len(prices), 2) if prices else None

    hist_avgs = {}
    for product in ALL_PRODUCTS:
        hist_avgs[product] = get_historical_average(product, days_back=7)

    return {
        "date": today.isoformat(),
        "results": results,
        "alerts": alerts,
        "daily_averages": daily_avgs,
        "historical_averages": hist_avgs,
        "stores_scraped": len(results),
        "alerts_count": len(alerts),
        "sika_products": SIKA_PRODUCTS,
        "competencia_products": COMPETENCIA_PRODUCTS,
        "product_names": PRODUCT_NAMES,
        "product_brands": PRODUCT_BRANDS,
    }
