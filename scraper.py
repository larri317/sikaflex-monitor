"""
Sikaflex Price Monitor - Scraper
Productos Sika: 522, 554, 621
Productos competencia: T930, T939, SF45, SS240, QT, SP101
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
    brand: str = "Sika"
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

    # ════════════════════════════════════════════
    # SIKA
    # ════════════════════════════════════════════
    {
        "store": "Andorra Campers",
        "url": "https://www.andorracampers.com/es/sikaflex-522-blanca_3485_342.html",
        "product": "522", "brand": "Sika",
        "selectors": ["span[itemprop='price']",".price","[data-price]"],
    },
    {
        "store": "Barna Campers",
        "url": "https://barnacampers.es/Sikaflex-52-BLANCO",
        "product": "522", "brand": "Sika",
        "selectors": ["span[itemprop='price']",".price","#our_price_display"],
    },
    {
        "store": "Madrid Camper 522",
        "url": "https://madridcamper.com/selladores-y-adhesivos/9522-sikaflex-522-blanco.html",
        "product": "522", "brand": "Sika",
        "selectors": ["span.current-price span[itemprop='price']","span.current-price","[itemprop='price']"],
    },
    {
        "store": "Obelink 522",
        "url": "https://www.obelink.es/sikaflex-522-kit-sellador-adhesivo-hibrido-white-628399.html",
        "product": "522", "brand": "Sika",
        "selectors": [".price--current","[data-price-amount]","span.price"],
    },
    {
        "store": "Intercut 554",
        "url": "https://intercut.es/products/sikaflex-554-300-ml-2284",
        "product": "554", "brand": "Sika",
        "selectors": [".price__current","span.price","[itemprop='price']"],
    },
    {
        "store": "Obelink 554",
        "url": "https://www.obelink.es/sikaflex-554-kit-de-montaje-black-628401.html",
        "product": "554", "brand": "Sika",
        "selectors": [".price--current","[data-price-amount]","span.price"],
    },
    {
        "store": "TodoCampers 554",
        "url": "https://todocampers.com/es/5041-sikaflex-554-negro-7612895736495.html",
        "product": "554", "brand": "Sika",
        "selectors": ["span.current-price span[itemprop='price']","span.current-price","[itemprop='price']"],
    },
    {
        "store": "Berger Camping 554",
        "url": "https://www.berger-camping.es/producto/adhesivo-de-montaje-sikaflex-554-sika-217196",
        "product": "554", "brand": "Sika",
        "selectors": [".price--current","[data-price]",".product__price"],
    },
    {
        "store": "Madrid Camper 554",
        "url": "https://madridcamper.com/selladores-y-adhesivos/9519-sikaflex-554-negro.html",
        "product": "554", "brand": "Sika",
        "selectors": ["span.current-price span[itemprop='price']","span.current-price","[itemprop='price']"],
    },
    {
        "store": "Toolstock 621",
        "url": "https://www.toolstock.info/principal/10201-SIKAFLEX-621CARTCH300CM3-NEGRO",
        "product": "621", "brand": "Sika",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Plana Online 621",
        "url": "https://planaonline.com/es/nautica-y-marina/sikaflex-621.html",
        "product": "621", "brand": "Sika",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },

    # ════════════════════════════════════════════
    # TEROSON
    # ════════════════════════════════════════════
    {
        "store": "MasQueCamper T930",
        "url": "https://www.masquecamper.com/producto/sellador-negro-terostat-ms-930-310-ml/",
        "product": "T930", "brand": "Teroson",
        "selectors": [".price","[itemprop='price']",".woocommerce-Price-amount","span.amount"],
    },
    {
        "store": "Intercut T930",
        "url": "https://intercut.es/products/teroson-ms-930-310ml-sellador-blanco-712",
        "product": "T930", "brand": "Teroson",
        "selectors": [".price__current","span.price","[itemprop='price']"],
    },
    {
        "store": "General Adhesivos T930",
        "url": "https://www.generaladhesivos.com/comprar-pegamento-teroson-ms-930-blanco-570ml-380",
        "product": "T930", "brand": "Teroson",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Suministros Torras T939",
        "url": "https://www.suministrostorras.com/es/producto/83538/teroson-ms-939-gris-290ml-adhesivo-elastico-monocomponente-78846",
        "product": "T939", "brand": "Teroson",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },

    # ════════════════════════════════════════════
    # SOUDAL
    # ════════════════════════════════════════════
    {
        "store": "Aismar SF45",
        "url": "https://www.poliuretanosaismar.com/tienda/resinas/reparacion-soudal/soudaflex-pu450-fc-300ml/",
        "product": "SF45", "brand": "Soudal",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },
    {
        "store": "Mengual SF45",
        "url": "https://www.mengual.com/soudaflex-45fc-adhesivo-sellador-de-poliuretano",
        "product": "SF45", "brand": "Soudal",
        "selectors": ["[itemprop='price']",".price","[data-price]"],
    },
    {
        "store": "Esteba SF45",
        "url": "https://www.esteba.com/es/adhesivo-sellador-pu-soudaflex-45fc",
        "product": "SF45", "brand": "Soudal",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Simor SS240",
        "url": "https://simor.es/producto/soudaseal-240-fc-290-ml/",
        "product": "SS240", "brand": "Soudal",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },
    {
        "store": "Mengual SS240",
        "url": "https://www.mengual.com/adhesivo-sellador-soudalseal-240fc-bolsa-de-600-ml",
        "product": "SS240", "brand": "Soudal",
        "selectors": ["[itemprop='price']",".price","[data-price]"],
    },
    {
        "store": "Ventigo SS240",
        "url": "https://www.ventigo.es/es_ES/p/sellador-adhesivo-ms-polimero-gris-soudaseal-240fc-tubo-290ml-unidad/5881/",
        "product": "SS240", "brand": "Soudal",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },

    # ════════════════════════════════════════════
    # QUIADSA
    # ════════════════════════════════════════════
    {
        "store": "Ferreteria Esmas QT",
        "url": "https://www.ferreteriaesmas.com/adhesivos-de-montaje/117-polimero-adhesivo-fija-plus-turbo-quiadsa-8425608305791.html",
        "product": "QT", "brand": "Quiadsa",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Destornillate QT",
        "url": "https://www.destornillate.es/producto/quiadsa-adhesivo-sellador-fija-plus-turbo-blanco-290ml/",
        "product": "QT", "brand": "Quiadsa",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },

    # ════════════════════════════════════════════
    # PATTEX SP101
    # ════════════════════════════════════════════
    {
        "store": "Carrefour SP101",
        "url": "https://www.carrefour.es/adhesivo-sellador-sp-101-gris-pattex/8410020407406/p",
        "product": "SP101", "brand": "Pattex",
        "selectors": ["[data-testid='product-price']",".product-price","[itemprop='price']",".price"],
    },
    {
        "store": "Leroy Merlin SP101",
        "url": "https://www.leroymerlin.es/productos/adhesivo-sellador-polimero-pegador-multimaterial-cartucho-280-ml-blanco-sp101-pattex-16027200.html",
        "product": "SP101", "brand": "Pattex",
        "selectors": ["[data-testid='price']",".price__amount","[itemprop='price']","span.price"],
    },
    {
        "store": "Amazon SP101 negro",
        "url": "https://www.amazon.es/Pattex-Sella-silicona-eficacia-fungicida/dp/B014WLHFL4",
        "product": "SP101", "brand": "Pattex",
        "selectors": [".a-price .a-offscreen","span.a-price-whole","#priceblock_ourprice"],
    },
    {
        "store": "Amazon SP101 transparente",
        "url": "https://www.amazon.es/Pattex-Original-Adhesivo-Interiores-Exteriores/dp/B08MW9RXS5",
        "product": "SP101", "brand": "Pattex",
        "selectors": [".a-price .a-offscreen","span.a-price-whole","#priceblock_ourprice"],
    },
    {
        "store": "Rubix SP101 negro",
        "url": "https://es.rubix.com/es/pattex-sp-101/p-G5010003635",
        "product": "SP101", "brand": "Pattex",
        "selectors": ["[itemprop='price']",".price",".product-price","span.price"],
    },
    {
        "store": "Rubix SP101 blanco",
        "url": "https://es.rubix.com/es/pattex-sp-101/p-G5010003636",
        "product": "SP101", "brand": "Pattex",
        "selectors": ["[itemprop='price']",".price",".product-price","span.price"],
    },
    {
        "store": "BricoTiendas SP101",
        "url": "https://www.bricotiendas.com/adhesivos-y-selladores/14828-sellador-pattex-sp101.html",
        "product": "SP101", "brand": "Pattex",
        "selectors": ["[itemprop='price']",".price",".product-price","span.price"],
    },
    {
        "store": "ModregoHogar SP101",
        "url": "https://www.modregohogar.com/ferreteria/silicona/siliconas-y-masillas/instant-tack-sp101-cartucho-blanco.html",
        "product": "SP101", "brand": "Pattex",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount","span.amount"],
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
                if 1 < val < 500:
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
                    brand=store_cfg.get("brand", "Sika"),
                    price=price,
                )

    full_text = soup.get_text()
    price = _extract_price_from_text(full_text)
    if price:
        logger.info(f"✓ {store_cfg['store']} [{store_cfg['product']}] → {price}€ (fallback)")
        return PriceResult(
            store=store_cfg["store"],
            url=store_cfg["url"],
            product=store_cfg["product"],
            brand=store_cfg.get("brand", "Sika"),
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
