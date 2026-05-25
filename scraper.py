"""
Sikaflex Price Monitor - Scraper
Busca precios de Sikaflex 522, 554 y 621 en tiendas online.
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from dataclasses import dataclass
from typing import Optional
import time
import random

logger = logging.getLogger(__name__)

@dataclass
class PriceResult:
    store: str
    url: str
    product: str
    price: float
    currency: str = "EUR"
    available: bool = True

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

STORES = [
    # ── Sikaflex 522 ──────────────────────────────────────────
    {
        "store": "Andorra Campers",
        "url": "https://www.andorracampers.com/es/sikaflex-522-blanca_3485_342.html",
        "product": "522",
        "selectors": [
            "span[itemprop='price']",
            ".price",
            ".product-price",
            "[data-price]",
        ],
    },
    {
        "store": "Barna Campers",
        "url": "https://barnacampers.es/Sikaflex-52-BLANCO",
        "product": "522",
        "selectors": [
            "span[itemprop='price']",
            ".price",
            ".our_price_display",
            "#our_price_display",
        ],
    },
    {
        "store": "Madrid Camper 522",
        "url": "https://madridcamper.com/selladores-y-adhesivos/9522-sikaflex-522-blanco.html",
        "product": "522",
        "selectors": [
            "span.current-price span[itemprop='price']",
            "span.current-price",
            "[itemprop='price']",
            ".price",
        ],
    },
    {
        "store": "ManoMano 522",
        "url": "https://www.manomano.es/cat/sikaflex+522",
        "product": "522",
        "selectors": [
            "[data-testid='price']",
            ".price",
            "span.price",
            "[itemprop='price']",
        ],
    },
    {
        "store": "Amazon ES 522",
        "url": "https://www.amazon.es/SIKA-522-LAMINA-BLANCO/dp/B08BZCXQCH",
        "product": "522",
        "selectors": [
            "span.a-price-whole",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "span.a-offscreen",
            ".a-price .a-offscreen",
        ],
    },

    # ── Sikaflex 554 ──────────────────────────────────────────
    {
        "store": "Amazon ES 554",
        "url": "https://www.amazon.es/Sika-Flex-554-Adhesivo-resistente-intemperie/dp/B09N7FFXS7",
        "product": "554",
        "selectors": [
            "span.a-price-whole",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "span.a-offscreen",
            ".a-price .a-offscreen",
        ],
    },
    {
        "store": "Leroy Merlin 554",
        "url": "https://www.leroymerlin.es/productos/sika-colle-de-montage-stp-flex-554-noir-300-ml-92946865.html",
        "product": "554",
        "selectors": [
            "[data-testid='price']",
            ".price__amount",
            "span.price",
            "[itemprop='price']",
        ],
    },
    {
        "store": "ManoMano 554",
        "url": "https://www.manomano.es/p/pegamento-de-montaje-sika-sikaflex-554-negro-300-ml-56632474",
        "product": "554",
        "selectors": [
            "[data-testid='price']",
            ".price",
            "span.price",
            "[itemprop='price']",
        ],
    },
    {
        "store": "Intercut 554",
        "url": "https://intercut.es/products/sikaflex-554-300-ml-2284",
        "product": "554",
        "selectors": [
            ".price__current",
            "span.price",
            "[itemprop='price']",
            ".product__price",
        ],
    },
    {
        "store": "Obelink 554",
        "url": "https://www.obelink.es/sikaflex-554-kit-de-montaje-black-628401.html",
        "product": "554",
        "selectors": [
            ".price--current",
            "[data-price-amount]",
            "span.price",
            "[itemprop='price']",
        ],
    },
    {
        "store": "TodoCampers 554",
        "url": "https://todocampers.com/es/5041-sikaflex-554-negro-7612895736495.html",
        "product": "554",
        "selectors": [
            "span.current-price span[itemprop='price']",
            "span.current-price",
            "[itemprop='price']",
            ".price",
        ],
    },
    {
        "store": "Berger Camping 554",
        "url": "https://www.berger-camping.es/producto/adhesivo-de-montaje-sikaflex-554-sika-217196",
        "product": "554",
        "selectors": [
            ".price--current",
            "[data-price]",
            ".product__price",
            "span.price",
        ],
    },
    {
        "store": "Madrid Camper 554",
        "url": "https://madridcamper.com/selladores-y-adhesivos/9519-sikaflex-554-negro.html",
        "product": "554",
        "selectors": [
            "span.current-price span[itemprop='price']",
            "span.current-price",
            "[itemprop='price']",
            ".price",
        ],
    },

    # ── Sikaflex 621 Purform ──────────────────────────────────
    {
        "store": "Toolstock 621",
        "url": "https://www.toolstock.info/principal/10201-SIKAFLEX-621CARTCH300CM3-NEGRO",
        "product": "621",
        "selectors": [
            "[itemprop='price']",
            ".price",
            ".product-price",
            "span.price",
        ],
    },
    {
        "store": "Plana Online 621",
        "url": "https://planaonline.com/es/nautica-y-marina/sikaflex-621.html",
        "product": "621",
        "selectors": [
            "[itemprop='price']",
            ".price",
            ".product-price",
            "span.price",
        ],
    },
]


def _extract_price_from_text(text: str) -> Optional[float]:
    patterns = [
        r"(\d{1,4}[.,]\d{2})\s*€",
        r"€\s*(\d{1,4}[.,]\d{2})",
        r"(\d{1,4}[.,]\d{2})",
    ]
    for pat in patterns:
        m = re.search(pat, text.strip())
        if m:
            raw = m.group(1).replace(".", "").replace(",", ".")
            try:
                val = float(raw)
                if 1 < val < 500:  # rango razonable para estos productos
                    return val
            except ValueError:
                continue
    return None


def _fetch_html(url: str, retries: int = 3) -> Optional[str]:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp.text
            logger.warning(f"HTTP {resp.status_code} en {url}")
        except requests.RequestException as e:
            logger.warning(f"Intento {attempt+1} fallido para {url}: {e}")
        time.sleep(random.uniform(2, 5))
    return None


def scrape_store(store_cfg: dict) -> Optional[PriceResult]:
    html = _fetch_html(store_cfg["url"])
    if not html:
        logger.error(f"No se pudo descargar {store_cfg['store']}")
        return None

    soup = BeautifulSoup(html, "html.parser")

    for selector in store_cfg.get("selectors", []):
        el = soup.select_one(selector)
        if el:
            raw = el.get("content") or el.get("data-price") or el.get_text()
            price = _extract_price_from_text(raw)
            if price:
                logger.info(f"✓ {store_cfg['store']} [{store_cfg['product']}] → {price}€")
                return PriceResult(
                    store=store_cfg["store"],
                    url=store_cfg["url"],
                    product=store_cfg["product"],
                    price=price,
                )

    # Fallback texto completo
    full_text = soup.get_text()
    price = _extract_price_from_text(full_text)
    if price:
        logger.info(f"✓ {store_cfg['store']} [{store_cfg['product']}] → {price}€ (fallback)")
        return PriceResult(
            store=store_cfg["store"],
            url=store_cfg["url"],
            product=store_cfg["product"],
            price=price,
        )

    logger.warning(f"✗ No se encontró precio en {store_cfg['store']}")
    return None


def scrape_all(delay_seconds: float = 2.0) -> list[PriceResult]:
    results = []
    for cfg in STORES:
        result = scrape_store(cfg)
        if result:
            results.append(result)
        time.sleep(delay_seconds + random.uniform(0, 1.5))
    return results
