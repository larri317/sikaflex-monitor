"""
Motor de alertas de precios con soporte de categorias.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional
import logging

from scraper import PriceResult
from database import get_historical_average, get_store_yesterday_price

logger = logging.getLogger(__name__)

ALERT_THRESHOLD = 0.10

CATEGORIES = {
    "Caravanas": ["522", "554", "T930", "SF45", "BP795"],
    "Marino":    ["591", "291i", "3M5200", "3M4200", "BP795"],
    "General":   ["621", "T939", "SS240", "QT", "SP101"],
}

SIKA_PRODUCTS = ["522", "554", "621", "591", "291i"]
COMP_PRODUCTS = ["T930", "T939", "SF45", "SS240", "QT", "SP101", "BP795", "3M5200", "3M4200"]
ALL_PRODUCTS  = SIKA_PRODUCTS + COMP_PRODUCTS

PRODUCT_NAMES = {
    "522":    "Sikaflex® 522",
    "554":    "Sikaflex® 554",
    "621":    "Sikaflex® 621 Purform",
    "591":    "Sikaflex® 591",
    "291i":   "Sikaflex® 291i",
    "T930":   "Teroson MS 930",
    "T939":   "Teroson MS 939",
    "SF45":   "Soudaflex 45 FC",
    "SS240":  "Soudaseal 240 FC",
    "QT":     "Quiadsa Turbo",
    "SP101":  "Pattex SP 101",
    "BP795":  "Bostik P795",
    "3M5200": "3M 5200",
    "3M4200": "3M 4200",
}

PRODUCT_BRANDS = {
    "522": "Sika", "554": "Sika", "621": "Sika",
    "591": "Sika", "291i": "Sika",
    "T930": "Teroson", "T939": "Teroson",
    "SF45": "Soudal", "SS240": "Soudal",
    "QT": "Quiadsa", "SP101": "Pattex",
    "BP795": "Bostik", "3M5200": "3M", "3M4200": "3M",
}

PRODUCT_CATEGORIES = {
    "522": "Caravanas", "554": "Caravanas",
    "591": "Marino", "291i": "Marino",
    "621": "General",
    "T930": "Caravanas", "SF45": "Caravanas", "BP795": "Caravanas",
    "3M5200": "Marino", "3M4200": "Marino",
    "T939": "General", "SS240": "General", "QT": "General", "SP101": "General",
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


def detect_alerts(results, threshold=ALERT_THRESHOLD):
    alerts = []
    for result in results:
        prev_price = get_store_yesterday_price(result.store, result.product)
        if prev_price:
            pct = (result.price - prev_price) / prev_price
            if abs(pct) > threshold:
                alerts.append(PriceAlert(
                    store=result.store, product=result.product, url=result.url,
                    current_price=result.price, reference_price=prev_price,
                    reference_type="precio anterior",
                    pct_change=round(pct * 100, 2),
                    alert_type="SUBIDA >10%" if pct > 0 else "BAJADA >10%",
                ))
            continue
        hist = get_historical_average(result.product, days_back=7)
        if hist:
            pct = (result.price - hist) / hist
            if abs(pct) > threshold:
                alerts.append(PriceAlert(
                    store=result.store, product=result.product, url=result.url,
                    current_price=result.price, reference_price=hist,
                    reference_type="media 7 días",
                    pct_change=round(pct * 100, 2),
                    alert_type="SUBIDA >10%" if pct > 0 else "BAJADA >10%",
                ))
        else:
            logger.info(f"ℹ️  {result.store} [{result.product}] — primer registro.")
    return alerts


def build_daily_summary(results, alerts, today=None):
    today = today or date.today()
    daily_avgs = {}
    for product in ALL_PRODUCTS:
        prices = [r.price for r in results if r.product == product]
        daily_avgs[product] = round(sum(prices)/len(prices), 2) if prices else None
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
        "comp_products": COMP_PRODUCTS,
        "all_products": ALL_PRODUCTS,
        "product_names": PRODUCT_NAMES,
        "product_brands": PRODUCT_BRANDS,
        "product_categories": PRODUCT_CATEGORIES,
        "categories": CATEGORIES,
    }
