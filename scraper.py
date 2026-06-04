"""
Sika Price Monitor - Scraper
Productos Sika: 522, 554, 621, 591, 291i
Competencia: T930, T939, SF45, SS240, QT, SP101, BP795, 3M5200, 3M4200
Categorias: Caravanas, Marino, General

Mejoras implementadas:
  1. Verificación de contexto del producto (keywords)
  2. Soporte Playwright para páginas con JavaScript
  3. Descarte de precios tachados / originales
  4. Tracking del selector usado por tienda
  5. Sanity check: alerta si el precio varía >30% respecto al anterior
  6. Rotación de User-Agent
  7. Script de test de selectores (función test_selectors)
  8. Modo debug por tienda (guarda HTML en disco si no encuentra precio)
"""

import requests
import re
import logging
import time
import random
import os
import json
from dataclasses import dataclass, field
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════
# MEJORA 6 — Rotación de User-Agent
# ══════════════════════════════════════════════════════════════
USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/17.4 Safari/605.1.15"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
    ),
]

def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


# ══════════════════════════════════════════════════════════════
# DATACLASS
# ══════════════════════════════════════════════════════════════
@dataclass
class PriceResult:
    store: str
    url: str
    product: str
    price: float
    brand: str = "Sika"
    category: str = "General"
    currency: str = "EUR"
    available: bool = True
    selector_usado: str = ""   # MEJORA 4


# ══════════════════════════════════════════════════════════════
# STORES
# ══════════════════════════════════════════════════════════════
STORES = [

    # ════════════════════════════════════════════
    # CARAVANAS — Sika
    # ════════════════════════════════════════════
    {
        "store": "Andorra Campers",
        "url": "https://www.andorracampers.com/es/sikaflex-522-blanca_3485_342.html",
        "product": "522", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span[itemprop='price']", ".price", "[data-price]"],
        "keywords": ["sikaflex", "522"],
    },
    {
        "store": "Barna Campers",
        "url": "https://barnacampers.es/Sikaflex-52-BLANCO",
        "product": "522", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span[itemprop='price']", ".price", "#our_price_display"],
        "keywords": ["sikaflex", "522"],
    },
    {
        "store": "Madrid Camper 522",
        "url": "https://madridcamper.com/selladores-y-adhesivos/9522-sikaflex-522-blanco.html",
        "product": "522", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span.current-price span[itemprop='price']", "span.current-price", "[itemprop='price']"],
        "keywords": ["sikaflex", "522"],
    },
    {
        "store": "Obelink 522",
        "url": "https://www.obelink.es/sikaflex-522-kit-sellador-adhesivo-hibrido-white-628399.html",
        "product": "522", "brand": "Sika", "category": "Caravanas",
        "selectors": [".price--current", "[data-price-amount]", "span.price"],
        "keywords": ["sikaflex", "522"],
    },
    {
        "store": "Intercut 554",
        "url": "https://intercut.es/products/sikaflex-554-300-ml-2284",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": [".price__current", "span.price", "[itemprop='price']"],
        "keywords": ["sikaflex", "554"],
    },
    {
        "store": "Obelink 554",
        "url": "https://www.obelink.es/sikaflex-554-kit-de-montaje-black-628401.html",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": [".price--current", "[data-price-amount]", "span.price"],
        "keywords": ["sikaflex", "554"],
    },
    {
        "store": "TodoCampers 554",
        "url": "https://todocampers.com/es/5041-sikaflex-554-negro-7612895736495.html",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span.current-price span[itemprop='price']", "span.current-price", "[itemprop='price']"],
        "keywords": ["sikaflex", "554"],
    },
    {
        "store": "Berger Camping 554",
        "url": "https://www.berger-camping.es/producto/adhesivo-de-montaje-sikaflex-554-sika-217196",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": [".price--current", "[data-price]", ".product__price"],
        "keywords": ["sikaflex", "554"],
    },
    {
        "store": "Madrid Camper 554",
        "url": "https://madridcamper.com/selladores-y-adhesivos/9519-sikaflex-554-negro.html",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span.current-price span[itemprop='price']", "span.current-price", "[itemprop='price']"],
        "keywords": ["sikaflex", "554"],
    },

    # ════════════════════════════════════════════
    # CARAVANAS — Competencia
    # ════════════════════════════════════════════
    {
        "store": "MasQueCamper T930",
        "url": "https://www.masquecamper.com/producto/sellador-negro-terostat-ms-930-310-ml/",
        "product": "T930", "brand": "Teroson", "category": "Caravanas",
        "selectors": [".price", "[itemprop='price']", ".woocommerce-Price-amount", "span.amount"],
        "keywords": ["teroson", "terostat", "930"],
    },
    {
        "store": "Intercut T930",
        "url": "https://intercut.es/products/teroson-ms-930-310ml-sellador-blanco-712",
        "product": "T930", "brand": "Teroson", "category": "Caravanas",
        "selectors": [".price__current", "span.price", "[itemprop='price']"],
        "keywords": ["teroson", "930"],
    },
    {
        "store": "Amazon BP795 blanco",
        "url": "https://www.amazon.es/Bostik-Poliuretano-profesional-interiores-exteriores/dp/B09TTD2PMP",
        "product": "BP795", "brand": "Bostik", "category": "Caravanas",
        "needs_js": True,
        "selectors": [
            "#corePrice_feature_div .a-offscreen",
            "#apex_offerDisplay_desktop .a-offscreen",
            ".a-price .a-offscreen",
            "span.a-price-whole",
            "#priceblock_ourprice",
        ],
        "keywords": ["bostik", "p795", "795"],
    },
    {
        "store": "ModregoHogar BP795",
        "url": "https://www.modregohogar.com/ferreteria/silicona/espumas-de-poliuretano/masilla-poliuretano-bostik-seal-n-flex-p795-gris-290ml.html",
        "product": "BP795", "brand": "Bostik", "category": "Caravanas",
        "selectors": ["[itemprop='price']", ".price", ".woocommerce-Price-amount"],
        "keywords": ["bostik", "p795", "795"],
    },
    {
        "store": "Diperplac BP795",
        "url": "https://diperplac.com/tienda/colas-masillas-y-siliconas/3850-bostik-masilla-poliuretano-p795-flex-300ml-blanca.html",
        "product": "BP795", "brand": "Bostik", "category": "Caravanas",
        "selectors": ["[itemprop='price']", ".price", ".woocommerce-Price-amount"],
        "keywords": ["bostik", "p795", "795"],
    },
    {
        "store": "Ferreteria Maquinaria BP795",
        "url": "https://ferreteriaymaquinaria.com/producto/masilla-pu-bostik-p795-premium-cartucho-300-ml/",
        "product": "BP795", "brand": "Bostik", "category": "Caravanas",
        "selectors": ["[itemprop='price']", ".price", ".woocommerce-Price-amount"],
        "keywords": ["bostik", "p795", "795"],
    },
    {
        "store": "Aismar SF45",
        "url": "https://www.poliuretanosaismar.com/tienda/resinas/reparacion-soudal/soudaflex-pu450-fc-300ml/",
        "product": "SF45", "brand": "Soudal", "category": "Caravanas",
        "selectors": ["[itemprop='price']", ".price", ".woocommerce-Price-amount"],
        "keywords": ["soudal", "soudaflex", "45"],
    },
    {
        "store": "Mengual SF45",
        "url": "https://www.mengual.com/soudaflex-45fc-adhesivo-sellador-de-poliuretano",
        "product": "SF45", "brand": "Soudal", "category": "Caravanas",
        "selectors": ["[itemprop='price']", ".price", "[data-price]"],
        "keywords": ["soudal", "soudaflex", "45"],
    },

    # ════════════════════════════════════════════
    # MARINO — Sika
    # ════════════════════════════════════════════
    {
        "store": "SVB Marine 591",
        "url": "https://www.svb-marine.es/es/sika-sellador-marino-sikaflex-591.html",
        "product": "591", "brand": "Sika", "category": "Marino",
        "selectors": [".product-price .current", "span.price", "[itemprop='price']"],
        "keywords": ["sikaflex", "591"],
    },
    {
        "store": "Francobordo 591",
        "url": "https://www.francobordo.com/sikaflex-591-sellador-de-bajas-emisiones-p-352421.html",
        "product": "591", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']", ".price", ".product-price"],
        "keywords": ["sikaflex", "591"],
    },
    {
        "store": "Netcoatings 591",
        "url": "https://netcoatings.shop/es/products/sikaflex-591-sellador-nautico-multiuso-pegamento-hibrido-para-barcos-sika-flex-blanco-300ml",
        "product": "591", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']", ".price", ".product__price"],
        "keywords": ["sikaflex", "591"],
    },
    {
        "store": "SVB Marine 291i",
        "url": "https://www.svb-marine.es/es/sika-sikaflex-sellador-marino-291i-para-juntas.html",
        "product": "291i", "brand": "Sika", "category": "Marino",
        "selectors": [".product-price .current", "span.price", "[itemprop='price']"],
        "keywords": ["sikaflex", "291"],
    },
    {
        "store": "GPS Nautico 291i",
        "url": "https://www.gpsnautico.com/es/accesorios-transductores/1684-sikaflex-291i-sellador-marino-300ml.html",
        "product": "291i", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']", ".price", ".product-price"],
        "keywords": ["sikaflex", "291"],
    },
    {
        "store": "Nautica Cadiz 291i",
        "url": "https://www.nauticacadiz.com/adhesivos-y-selladores-embarcaciones/sikaflex-marino-291-sellador-poliuretano",
        "product": "291i", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']", ".price", ".woocommerce-Price-amount"],
        "keywords": ["sikaflex", "291"],
    },
    {
        "store": "Naval Chicolino 291i",
        "url": "https://navalchicolino.com/producto/sikaflex-marino-291-blanco-o-negro/",
        "product": "291i", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']", ".price", ".woocommerce-Price-amount"],
        "keywords": ["sikaflex", "291"],
    },

    # ════════════════════════════════════════════
    # MARINO — Competencia
    # ════════════════════════════════════════════
    {
        "store": "Waveinn 3M5200",
        "url": "https://www.tradeinn.com/waveinn/es/3m-sellador-adhesivo-marino-5200/1288948/p",
        "product": "3M5200", "brand": "3M", "category": "Marino",
        "selectors": ["[data-testid='price']", ".price", "[itemprop='price']", ".product-price"],
        "keywords": ["3m", "5200"],
    },
    {
        "store": "A.Alvarez 3M5200",
        "url": "https://www.a-alvarez.com/51842-sellador-adhesivo-3m-secado-rapido-5200",
        "product": "3M5200", "brand": "3M", "category": "Marino",
        "selectors": ["[itemprop='price']", ".price", ".product-price"],
        "keywords": ["3m", "5200"],
    },
    {
        "store": "Waveinn 3M4200",
        "url": "https://www.tradeinn.com/waveinn/es/3m-sellador-adhesivo-marino-de-curado-rapido-4200/1288954/p",
        "product": "3M4200", "brand": "3M", "category": "Marino",
        "selectors": ["[data-testid='price']", ".price", "[itemprop='price']", ".product-price"],
        "keywords": ["3m", "4200"],
    },
    {
        "store": "Shop-SKS 3M4200",
        "url": "https://www.shop-sks.com/es/3M-Adhesivo-y-sellador-de-poliuretano-marino-4200-FC-negro-310-ml",
        "product": "3M4200", "brand": "3M", "category": "Marino",
        "selectors": ["[itemprop='price']", ".price", ".product-price"],
        "keywords": ["3m", "4200"],
    },
    {
        "store": "Amazon BP795 marino",
        "url": "https://www.amazon.es/Bostik-Poliuretano-profesional-interiores-exteriores/dp/B09TTD2PMP",
        "product": "BP795", "brand": "Bostik", "category": "Marino",
        "needs_js": True,
        "selectors": [
            "#corePrice_feature_div .a-offscreen",
            "#apex_offerDisplay_desktop .a-offscreen",
            ".a-price .a-offscreen",
            "span.a-price-whole",
            "#priceblock_ourprice",
        ],
        "keywords": ["bostik", "p795", "795"],
    },

    # ════════════════════════════════════════════
    # GENERAL — Sika
    # ════════════════════════════════════════════
    {
        "store": "Toolstock 621",
        "url": "https://www.toolstock.info/principal/10201-SIKAFLEX-621CARTCH300CM3-NEGRO",
        "product": "621", "brand": "Sika", "category": "General",
        "selectors": ["[itemprop='price']", ".price", ".product-price"],
        "keywords": ["sikaflex", "621"],
    },
    {
        "store": "Plana Online 621",
        "url": "https://planaonline.com/es/nautica-y-marina/sikaflex-621.html",
        "product": "621", "brand": "Sika", "category": "General",
        "selectors": ["[itemprop='price']", ".price", ".product-price"],
        "keywords": ["sikaflex", "621"],
    },

    # ════════════════════════════════════════════
    # GENERAL — Competencia
    # ════════════════════════════════════════════
    {
        "store": "Suministros Torras T939",
        "url": "https://www.suministrostorras.com/es/producto/83538/teroson-ms-939-gris-290ml-adhesivo-elastico-monocomponente-78846",
        "product": "T939", "brand": "Teroson", "category": "General",
        "selectors": ["[itemprop='price']", ".price", ".product-price"],
        "keywords": ["teroson", "939"],
    },
    {
        "store": "Simor SS240",
        "url": "https://simor.es/producto/soudaseal-240-fc-290-ml/",
        "product": "SS240", "brand": "Soudal", "category": "General",
        "selectors": ["[itemprop='price']", ".price", ".woocommerce-Price-amount"],
        "keywords": ["soudal", "soudaseal", "240"],
    },
    {
        "store": "Mengual SS240",
        "url": "https://www.mengual.com/adhesivo-sellador-soudalseal-240fc-bolsa-de-600-ml",
        "product": "SS240", "brand": "Soudal", "category": "General",
        "selectors": ["[itemprop='price']", ".price", "[data-price]"],
        "keywords": ["soudal", "soudaseal", "240"],
    },
    {
        "store": "Ferreteria Esmas QT",
        "url": "https://www.ferreteriaesmas.com/adhesivos-de-montaje/117-polimero-adhesivo-fija-plus-turbo-quiadsa-8425608305791.html",
        "product": "QT", "brand": "Quiadsa", "category": "General",
        "selectors": ["[itemprop='price']", ".price", ".product-price"],
        "keywords": ["quiadsa", "fija plus", "turbo"],
    },
    {
        "store": "Destornillate QT",
        "url": "https://www.destornillate.es/producto/quiadsa-adhesivo-sellador-fija-plus-turbo-blanco-290ml/",
        "product": "QT", "brand": "Quiadsa", "category": "General",
        "selectors": ["[itemprop='price']", ".price", ".woocommerce-Price-amount"],
        "keywords": ["quiadsa", "fija plus", "turbo"],
    },
    {
        "store": "Carrefour SP101",
        "url": "https://www.carrefour.es/adhesivo-sellador-sp-101-gris-pattex/8410020407406/p",
        "product": "SP101", "brand": "Pattex", "category": "General",
        "needs_js": True,
        "selectors": ["[data-testid='product-price']", ".product-price", "[itemprop='price']"],
        "keywords": ["pattex", "sp101", "sp-101"],
    },
    {
        "store": "Leroy Merlin SP101",
        "url": "https://www.leroymerlin.es/productos/adhesivo-sellador-polimero-pegador-multimaterial-cartucho-280-ml-blanco-sp101-pattex-16027200.html",
        "product": "SP101", "brand": "Pattex", "category": "General",
        "needs_js": True,
        "selectors": ["[data-testid='price']", ".price__amount", "[itemprop='price']"],
        "keywords": ["pattex", "sp101", "sp-101"],
    },
    {
        "store": "Amazon SP101",
        "url": "https://www.amazon.es/Pattex-Sella-silicona-eficacia-fungicida/dp/B014WLHFL4",
        "product": "SP101", "brand": "Pattex", "category": "General",
        "needs_js": True,
        "selectors": [
            "#corePrice_feature_div .a-offscreen",
            "#apex_offerDisplay_desktop .a-offscreen",
            ".a-price .a-offscreen",
            "span.a-price-whole",
            "#priceblock_ourprice",
        ],
        "keywords": ["pattex", "sp101"],
    },
    {
        "store": "Ventigo SS240",
        "url": "https://www.ventigo.es/es_ES/p/sellador-adhesivo-ms-polimero-gris-soudaseal-240fc-tubo-290ml-unidad/5881/",
        "product": "SS240", "brand": "Soudal", "category": "General",
        "selectors": ["[itemprop='price']", ".price", ".product-price"],
        "keywords": ["soudal", "soudaseal", "240"],
    },
]


# ══════════════════════════════════════════════════════════════
# RANGOS DE PRECIOS
# ══════════════════════════════════════════════════════════════
PRICE_RANGES = {
    "522":    (5, 40),
    "554":    (8, 50),
    "621":    (8, 50),
    "591":    (10, 60),
    "291i":   (8, 50),
    "T930":   (8, 60),
    "T939":   (8, 60),
    "SF45":   (3, 30),
    "SS240":  (5, 40),
    "QT":     (3, 25),
    "SP101":  (3, 25),
    "BP795":  (5, 30),
    "3M5200": (15, 80),
    "3M4200": (12, 70),
}

# Contenedores donde buscar en el fallback
FALLBACK_CONTAINERS = [
    "[id*='product-detail']",
    "[class*='product-detail']",
    "[id*='product-info']",
    "[class*='product-info']",
    "[class*='product-main']",
    "[class*='product-summary']",
    "[id*='main-product']",
    "article.product",
    "div.product",
    "main",
    "#content",
    "#main",
]

# Directorio para guardar HTML de debug
DEBUG_DIR = "debug_html"


# ══════════════════════════════════════════════════════════════
# MEJORA 3 — Eliminar nodos de precio tachado / original
# ══════════════════════════════════════════════════════════════
STRIKE_SELECTORS = [
    "s", "del",
    ".price--old", ".price-old", ".old-price",
    ".was-price", ".price__was",
    "[class*='original-price']", "[class*='price-before']",
    "[class*='regular-price']", ".precio-antes",
]

def _remove_struck_prices(soup: BeautifulSoup) -> BeautifulSoup:
    """Elimina del árbol DOM los nodos que contienen precios tachados/originales."""
    for sel in STRIKE_SELECTORS:
        for node in soup.select(sel):
            node.decompose()
    return soup


# ══════════════════════════════════════════════════════════════
# EXTRACCIÓN DE PRECIO
# ══════════════════════════════════════════════════════════════
def _extract_price_from_text(text: str, min_price: float = 3.0, max_price: float = 200.0) -> Optional[float]:
    """Devuelve el PRIMER precio válido encontrado en el texto (no el mínimo)."""
    patterns = [
        r"(\d{1,4}[.,]\d{2})\s*€",
        r"€\s*(\d{1,4}[.,]\d{2})",
        r"(\d{1,4}[.,]\d{2})",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text.strip()):
            raw = m.group(1).replace(".", "").replace(",", ".")
            try:
                val = float(raw)
                if min_price <= val <= max_price:
                    return val
            except ValueError:
                continue
    return None


# ══════════════════════════════════════════════════════════════
# MEJORA 1 — Verificación de contexto del producto
# ══════════════════════════════════════════════════════════════
def _verify_product_context(soup: BeautifulSoup, keywords: list[str]) -> bool:
    """
    Comprueba que la página contiene al menos una de las keywords del producto.
    Evita aceptar precios de páginas erróneas o redirigidas.
    """
    if not keywords:
        return True
    page_text = soup.get_text().lower()
    return any(kw.lower() in page_text for kw in keywords)


# ══════════════════════════════════════════════════════════════
# MEJORA 5 — Sanity check vs precio anterior
# ══════════════════════════════════════════════════════════════
def _sanity_check(store: str, product: str, new_price: float,
                  last_prices: dict, threshold: float = 0.30) -> bool:
    """
    Alerta si el precio nuevo difiere >30% del último registrado.
    Devuelve True si el precio parece válido, False si es sospechoso.
    """
    key = f"{store}_{product}"
    last = last_prices.get(key)
    if last is None:
        return True  # Sin histórico, aceptar
    diff = abs(new_price - last) / last
    if diff > threshold:
        logger.warning(
            f"⚠ SANITY CHECK [{store}] [{product}]: "
            f"precio anterior {last}€ → nuevo {new_price}€ "
            f"(variación {diff:.0%}, umbral {threshold:.0%}). "
            f"Verificar manualmente."
        )
        return False
    return True


def load_last_prices(csv_path: str = "prices.csv") -> dict:
    """
    Lee el CSV de precios y devuelve el último precio conocido
    por tienda+producto como dict {store_product: precio}.
    """
    last = {}
    if not os.path.exists(csv_path):
        return last
    try:
        import csv
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row.get('store', '')}_{row.get('product', '')}"
                try:
                    last[key] = float(row.get("price", 0))
                except ValueError:
                    pass
    except Exception as e:
        logger.warning(f"No se pudo leer histórico de precios: {e}")
    return last


# ══════════════════════════════════════════════════════════════
# MEJORA 2 — Playwright para páginas con JS
# ══════════════════════════════════════════════════════════════
def _fetch_html_playwright(url: str) -> Optional[str]:
    """
    Descarga el HTML renderizado con Playwright (ejecuta JS).
    Requiere: pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                extra_http_headers={"Accept-Language": "es-ES,es;q=0.9"},
            )
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Esperar a que aparezca algún elemento de precio
            try:
                page.wait_for_selector(
                    "[itemprop='price'], .price, .a-price",
                    timeout=8000,
                )
            except Exception:
                pass  # Continuar igualmente
            html = page.content()
            browser.close()
            return html
    except ImportError:
        logger.warning(
            "Playwright no instalado. Instalar con: "
            "pip install playwright && playwright install chromium"
        )
        return None
    except Exception as e:
        logger.warning(f"Playwright falló en {url}: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# DESCARGA DE HTML
# ══════════════════════════════════════════════════════════════
def _fetch_html(url: str, needs_js: bool = False, retries: int = 3) -> Optional[str]:
    # MEJORA 2: usar Playwright si la tienda lo requiere
    if needs_js:
        html = _fetch_html_playwright(url)
        if html:
            return html
        logger.warning(f"Playwright falló, reintentando con requests: {url}")

    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=_get_headers(), timeout=20)
            if resp.status_code == 200:
                return resp.text
            logger.warning(f"HTTP {resp.status_code} en {url}")
        except requests.RequestException as e:
            logger.warning(f"Intento {attempt + 1} fallido para {url}: {e}")
        time.sleep(random.uniform(2, 5))
    return None


# ══════════════════════════════════════════════════════════════
# MEJORA 8 — Guardar HTML de debug
# ══════════════════════════════════════════════════════════════
def _save_debug_html(store_name: str, html: str) -> None:
    """Guarda el HTML en disco para inspección manual cuando no se encuentra precio."""
    os.makedirs(DEBUG_DIR, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", store_name)
    path = os.path.join(DEBUG_DIR, f"{safe_name}.html")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"🔍 HTML de debug guardado en: {path}")
    except Exception as e:
        logger.warning(f"No se pudo guardar HTML de debug: {e}")


# ══════════════════════════════════════════════════════════════
# SCRAPING PRINCIPAL
# ══════════════════════════════════════════════════════════════
def scrape_store(store_cfg: dict, last_prices: dict = None, debug: bool = False) -> Optional[PriceResult]:
    if last_prices is None:
        last_prices = {}

    needs_js = store_cfg.get("needs_js", False)
    html = _fetch_html(store_cfg["url"], needs_js=needs_js)
    if not html:
        logger.error(f"No se pudo descargar {store_cfg['store']}")
        return None

    product = store_cfg["product"]
    min_p, max_p = PRICE_RANGES.get(product, (3, 200))
    keywords = store_cfg.get("keywords", [])

    soup = BeautifulSoup(html, "html.parser")

    # MEJORA 1 — Verificar que la página corresponde al producto esperado
    if not _verify_product_context(soup, keywords):
        logger.warning(
            f"⚠ {store_cfg['store']} [{product}]: la página no contiene "
            f"las keywords {keywords}. Posible redirección o error de URL."
        )
        if debug:
            _save_debug_html(store_cfg["store"], html)
        return None

    # MEJORA 3 — Eliminar precios tachados antes de buscar
    soup = _remove_struck_prices(soup)

    # ── 1. Selectores específicos de la tienda ──
    for selector in store_cfg.get("selectors", []):
        el = soup.select_one(selector)
        if el:
            raw = el.get("content") or el.get("data-price") or el.get_text()
            price = _extract_price_from_text(raw, min_p, max_p)
            if price:
                # MEJORA 5 — Sanity check
                if not _sanity_check(store_cfg["store"], product, price, last_prices):
                    if debug:
                        _save_debug_html(store_cfg["store"], html)
                    return None
                logger.info(f"✓ {store_cfg['store']} [{product}] → {price}€  (selector: {selector})")
                return PriceResult(
                    store=store_cfg["store"],
                    url=store_cfg["url"],
                    product=product,
                    brand=store_cfg.get("brand", "Sika"),
                    category=store_cfg.get("category", "General"),
                    price=price,
                    selector_usado=selector,   # MEJORA 4
                )

    # ── 2. Fallback: contenedores del producto ──
    logger.warning(
        f"⚠ {store_cfg['store']} [{product}]: ningún selector funcionó, "
        f"intentando fallback por contenedor"
    )
    for container_selector in FALLBACK_CONTAINERS:
        container = soup.select_one(container_selector)
        if container:
            price = _extract_price_from_text(container.get_text(), min_p, max_p)
            if price:
                if not _sanity_check(store_cfg["store"], product, price, last_prices):
                    if debug:
                        _save_debug_html(store_cfg["store"], html)
                    return None
                logger.info(
                    f"✓ {store_cfg['store']} [{product}] → {price}€  "
                    f"(fallback contenedor: {container_selector})"
                )
                return PriceResult(
                    store=store_cfg["store"],
                    url=store_cfg["url"],
                    product=product,
                    brand=store_cfg.get("brand", "Sika"),
                    category=store_cfg.get("category", "General"),
                    price=price,
                    selector_usado=f"fallback:{container_selector}",  # MEJORA 4
                )

    # ── 3. Sin precio — guardar debug si está activado ──
    logger.warning(
        f"✗ {store_cfg['store']} [{product}]: sin precio válido "
        f"(rango {min_p}–{max_p}€). Revisar selectores o estructura de la página."
    )
    if debug:
        _save_debug_html(store_cfg["store"], html)  # MEJORA 8
    return None


# ══════════════════════════════════════════════════════════════
# MEJORA 7 — Test de selectores para una tienda
# ══════════════════════════════════════════════════════════════
def test_selectors(store_cfg: dict) -> None:
    """
    Descarga la página y prueba todos los selectores definidos,
    mostrando qué texto encuentra cada uno. Útil para depurar
    sin ejecutar el scraper completo.

    Uso:
        from scraper import STORES, test_selectors
        test_selectors(next(s for s in STORES if s["store"] == "Obelink 522"))
    """
    print(f"\n{'='*60}")
    print(f"TEST DE SELECTORES: {store_cfg['store']}")
    print(f"URL: {store_cfg['url']}")
    print(f"{'='*60}")

    needs_js = store_cfg.get("needs_js", False)
    html = _fetch_html(store_cfg["url"], needs_js=needs_js)
    if not html:
        print("ERROR: No se pudo descargar la página.")
        return

    product = store_cfg["product"]
    min_p, max_p = PRICE_RANGES.get(product, (3, 200))
    soup = BeautifulSoup(html, "html.parser")

    # Verificación de keywords
    keywords = store_cfg.get("keywords", [])
    context_ok = _verify_product_context(soup, keywords)
    print(f"\n[Contexto] Keywords {keywords}: {'✓ encontradas' if context_ok else '✗ NO encontradas — posible página incorrecta'}")

    print(f"\n[Selectores específicos]")
    for selector in store_cfg.get("selectors", []):
        el = soup.select_one(selector)
        if el:
            raw = el.get("content") or el.get("data-price") or el.get_text()
            price = _extract_price_from_text(raw.strip(), min_p, max_p)
            print(f"  {selector}")
            print(f"    Texto raw : {raw.strip()[:80]!r}")
            print(f"    Precio    : {price}€" if price else "    Precio    : (no encontrado en rango)")
        else:
            print(f"  {selector} → (elemento no encontrado en DOM)")

    print(f"\n[Fallback contenedores]")
    for cs in FALLBACK_CONTAINERS:
        container = soup.select_one(cs)
        if container:
            price = _extract_price_from_text(container.get_text(), min_p, max_p)
            print(f"  {cs} → {'✓ ' + str(price) + '€' if price else '(sin precio válido)'}")

    print(f"\n[Precios tachados eliminados — resultado limpio]")
    soup_clean = _remove_struck_prices(BeautifulSoup(html, "html.parser"))
    for selector in store_cfg.get("selectors", []):
        el = soup_clean.select_one(selector)
        if el:
            raw = el.get("content") or el.get("data-price") or el.get_text()
            price = _extract_price_from_text(raw.strip(), min_p, max_p)
            if price:
                print(f"  {selector} → ✓ {price}€ (tras limpiar tachados)")

    print(f"{'='*60}\n")


# ══════════════════════════════════════════════════════════════
# SCRAPING COMPLETO
# ══════════════════════════════════════════════════════════════
def scrape_all(delay_seconds: float = 2.0, debug: bool = False) -> list[PriceResult]:
    # MEJORA 5: cargar histórico de precios para el sanity check
    last_prices = load_last_prices()

    results = []
    for cfg in STORES:
        result = scrape_store(cfg, last_prices=last_prices, debug=debug)
        if result:
            results.append(result)
        time.sleep(delay_seconds + random.uniform(0, 1.5))
    return results
