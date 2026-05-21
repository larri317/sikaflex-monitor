"""
Sikaflex Price Monitor - Scraper
Busca precios de Sikaflex 522 y 621 Purform en tiendas online españolas.
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
    product: str          # "522" o "621"
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

# ─────────────────────────────────────────────────────────────
# TIENDAS CONFIGURADAS
# Añade o elimina tiendas aquí. Cada entrada tiene:
#   - store:   nombre visible
#   - url:     página del producto
#   - product: "522" o "621"
#   - selectors: lista de selectores CSS a probar (el primero que funcione)
#   - pattern:   regex alternativo si los selectores fallan
# ─────────────────────────────────────────────────────────────
STORES = [
    # ── Sikaflex 522 ──────────────────────────────────────────
    {
        "store": "TodoCampers",
        "url": "https://todocampers.com/es/5039-sikaflex-522-negro-7612895733593.html",
        "product": "522",
        "selectors": [
            "span.current-price span[itemprop='price']",
            "span.price",
            ".product-price",
        ],
    },
    {
        "store": "Berger Camping",
        "url": "https://www.berger-camping.es/producto/sellador-adhesivo-sika-sikaflex-522-217185",
        "product": "522",
        "selectors": [
            ".price--current",
            "[data-price]",
            ".product__price",
        ],
    },
    {
        "store": "SVB Marine ES",
        "url": "https://www.svb-marine.es/es/sika-sikaflex-sellador-y-adhesivo-522.html",
        "product": "522",
        "selectors": [
            ".product-price .current",
            "span.price",
            "[itemprop='price']",
        ],
    },
    {
        "store": "Mi Tortuga",
        "url": "https://www.mitortuga.es/productos/sikaflex-522-blanco-sellador-polimero-cartucho-300ml-especial-caravanas-autocaravanas-ref",
        "product": "522",
        "selectors": [
            ".price",
            "[itemprop='price']",
            ".product-price",
        ],
    },
    {
        "store": "Madrid Camper",
        "url": "https://madridcamper.com/selladores-y-adhesivos/9523-sikaflex-522-negro.html",
        "product": "522",
        "selectors": [
            "span.current-price",
            "[itemprop='price']",
            ".price",
        ],
    },
    {
        "store": "Obelink ES",
        "url": "https://www.obelink.es/sikaflex-522-kit-sellador-adhesivo-hibrido-white-628399.html",
        "product": "522",
        "selectors": [
            ".price--current",
            "[data-price-amount]",
            ".product-single__price",
        ],
    },

    # ── Sikaflex 621 Purform ──────────────────────────────────
    # NOTA: el 621 es más nuevo; añade URLs cuando encuentres tiendas.
    # Las URLs de ejemplo abajo deben verificarse y actualizarse.
    {
        "store": "Sika ES Oficial",
        "url": "https://esp.sika.com/es/industria/transporte/selladores/selladores-exteriores/sikaflex-621-purform.html",
        "product": "621",
        "selectors": [
            ".price",
            "[itemprop='price']",
            ".product-price",
        ],
    },
]


def _extract_price_from_text(text: str) -> Optional[float]:
    """Extrae el primer precio numérico de un texto."""
    # Cubre formatos: 12,50 € / €12.50 / 12.50€ / 12,50
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
                return float(raw)
            except ValueError:
                continue
    return None


def _fetch_html(url: str, retries: int = 3) -> Optional[str]:
    """Descarga el HTML de una URL con reintentos y backoff."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp.text
            logger.warning(f"HTTP {resp.status_code} en {url}")
        except requests.RequestException as e:
            logger.warning(f"Intento {attempt+1} fallido para {url}: {e}")
        time.sleep(random.uniform(2, 5))  # pausa educada entre reintentos
    return None


def scrape_store(store_cfg: dict) -> Optional[PriceResult]:
    """Extrae el precio de una tienda usando la configuración dada."""
    html = _fetch_html(store_cfg["url"])
    if not html:
        logger.error(f"No se pudo descargar {store_cfg['store']}")
        return None

    soup = BeautifulSoup(html, "html.parser")

    # 1) Probar selectores CSS en orden
    for selector in store_cfg.get("selectors", []):
        el = soup.select_one(selector)
        if el:
            # Intentar atributo 'content' primero (microdatos), luego texto
            raw = el.get("content") or el.get_text()
            price = _extract_price_from_text(raw)
            if price and price > 0:
                logger.info(f"✓ {store_cfg['store']} [{store_cfg['product']}] → {price}€  (selector: {selector})")
                return PriceResult(
                    store=store_cfg["store"],
                    url=store_cfg["url"],
                    product=store_cfg["product"],
                    price=price,
                )

    # 2) Fallback: buscar en todo el texto de la página
    full_text = soup.get_text()
    price = _extract_price_from_text(full_text)
    if price and price > 0:
        logger.info(f"✓ {store_cfg['store']} [{store_cfg['product']}] → {price}€  (fallback texto)")
        return PriceResult(
            store=store_cfg["store"],
            url=store_cfg["url"],
            product=store_cfg["product"],
            price=price,
        )

    logger.warning(f"✗ No se encontró precio en {store_cfg['store']}")
    return None


def scrape_all(delay_seconds: float = 2.0) -> list[PriceResult]:
    """Scrape todas las tiendas configuradas."""
    results = []
    for cfg in STORES:
        result = scrape_store(cfg)
        if result:
            results.append(result)
        time.sleep(delay_seconds + random.uniform(0, 1.5))  # cortesía
    return results
