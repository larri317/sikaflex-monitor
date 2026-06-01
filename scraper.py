"""
Sika Price Monitor - Scraper
Productos Sika: 522, 554, 621, 591, 291i
Competencia: T930, T939, SF45, SS240, QT, SP101, BP795, 3M5200, 3M4200
Categorias: Caravanas, Marino, General
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
    category: str = "General"
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
    # CARAVANAS — Sika
    # ════════════════════════════════════════════
    {
        "store": "Andorra Campers",
        "url": "https://www.andorracampers.com/es/sikaflex-522-blanca_3485_342.html",
        "product": "522", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span[itemprop='price']",".price","[data-price]"],
    },
    {
        "store": "Barna Campers",
        "url": "https://barnacampers.es/Sikaflex-52-BLANCO",
        "product": "522", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span[itemprop='price']",".price","#our_price_display"],
    },
    {
        "store": "Madrid Camper 522",
        "url": "https://madridcamper.com/selladores-y-adhesivos/9522-sikaflex-522-blanco.html",
        "product": "522", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span.current-price span[itemprop='price']","span.current-price","[itemprop='price']"],
    },
    {
        "store": "Obelink 522",
        "url": "https://www.obelink.es/sikaflex-522-kit-sellador-adhesivo-hibrido-white-628399.html",
        "product": "522", "brand": "Sika", "category": "Caravanas",
        "selectors": [".price--current","[data-price-amount]","span.price"],
    },
    {
        "store": "Intercut 554",
        "url": "https://intercut.es/products/sikaflex-554-300-ml-2284",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": [".price__current","span.price","[itemprop='price']"],
    },
    {
        "store": "Obelink 554",
        "url": "https://www.obelink.es/sikaflex-554-kit-de-montaje-black-628401.html",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": [".price--current","[data-price-amount]","span.price"],
    },
    {
        "store": "TodoCampers 554",
        "url": "https://todocampers.com/es/5041-sikaflex-554-negro-7612895736495.html",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span.current-price span[itemprop='price']","span.current-price","[itemprop='price']"],
    },
    {
        "store": "Berger Camping 554",
        "url": "https://www.berger-camping.es/producto/adhesivo-de-montaje-sikaflex-554-sika-217196",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": [".price--current","[data-price]",".product__price"],
    },
    {
        "store": "Madrid Camper 554",
        "url": "https://madridcamper.com/selladores-y-adhesivos/9519-sikaflex-554-negro.html",
        "product": "554", "brand": "Sika", "category": "Caravanas",
        "selectors": ["span.current-price span[itemprop='price']","span.current-price","[itemprop='price']"],
    },

    # ════════════════════════════════════════════
    # CARAVANAS — Competencia
    # ════════════════════════════════════════════
    {
        "store": "MasQueCamper T930",
        "url": "https://www.masquecamper.com/producto/sellador-negro-terostat-ms-930-310-ml/",
        "product": "T930", "brand": "Teroson", "category": "Caravanas",
        "selectors": [".price","[itemprop='price']",".woocommerce-Price-amount","span.amount"],
    },
    {
        "store": "Intercut T930",
        "url": "https://intercut.es/products/teroson-ms-930-310ml-sellador-blanco-712",
        "product": "T930", "brand": "Teroson", "category": "Caravanas",
        "selectors": [".price__current","span.price","[itemprop='price']"],
    },
    {
        "store": "Amazon BP795 blanco",
        "url": "https://www.amazon.es/Bostik-Poliuretano-profesional-interiores-exteriores/dp/B09TTD2PMP",
        "product": "BP795", "brand": "Bostik", "category": "Caravanas",
        "selectors": [".a-price .a-offscreen","span.a-price-whole","#priceblock_ourprice"],
    },
    {
        "store": "ModregoHogar BP795",
        "url": "https://www.modregohogar.com/ferreteria/silicona/espumas-de-poliuretano/masilla-poliuretano-bostik-seal-n-flex-p795-gris-290ml.html",
        "product": "BP795", "brand": "Bostik", "category": "Caravanas",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },
    {
        "store": "Diperplac BP795",
        "url": "https://diperplac.com/tienda/colas-masillas-y-siliconas/3850-bostik-masilla-poliuretano-p795-flex-300ml-blanca.html",
        "product": "BP795", "brand": "Bostik", "category": "Caravanas",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },
    {
        "store": "Ferreteria Maquinaria BP795",
        "url": "https://ferreteriaymaquinaria.com/producto/masilla-pu-bostik-p795-premium-cartucho-300-ml/",
        "product": "BP795", "brand": "Bostik", "category": "Caravanas",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },
    {
        "store": "Aismar SF45",
        "url": "https://www.poliuretanosaismar.com/tienda/resinas/reparacion-soudal/soudaflex-pu450-fc-300ml/",
        "product": "SF45", "brand": "Soudal", "category": "Caravanas",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },
    {
        "store": "Mengual SF45",
        "url": "https://www.mengual.com/soudaflex-45fc-adhesivo-sellador-de-poliuretano",
        "product": "SF45", "brand": "Soudal", "category": "Caravanas",
        "selectors": ["[itemprop='price']",".price","[data-price]"],
    },

    # ════════════════════════════════════════════
    # MARINO — Sika
    # ════════════════════════════════════════════
    {
        "store": "SVB Marine 591",
        "url": "https://www.svb-marine.es/es/sika-sellador-marino-sikaflex-591.html",
        "product": "591", "brand": "Sika", "category": "Marino",
        "selectors": [".product-price .current","span.price","[itemprop='price']"],
    },
    {
        "store": "Francobordo 591",
        "url": "https://www.francobordo.com/sikaflex-591-sellador-de-bajas-emisiones-p-352421.html",
        "product": "591", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Netcoatings 591",
        "url": "https://netcoatings.shop/es/products/sikaflex-591-sellador-nautico-multiuso-pegamento-hibrido-para-barcos-sika-flex-blanco-300ml",
        "product": "591", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']",".price",".product__price"],
    },
    {
        "store": "SVB Marine 291i",
        "url": "https://www.svb-marine.es/es/sika-sikaflex-sellador-marino-291i-para-juntas.html",
        "product": "291i", "brand": "Sika", "category": "Marino",
        "selectors": [".product-price .current","span.price","[itemprop='price']"],
    },
    {
        "store": "GPS Nautico 291i",
        "url": "https://www.gpsnautico.com/es/accesorios-transductores/1684-sikaflex-291i-sellador-marino-300ml.html",
        "product": "291i", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Nautica Cadiz 291i",
        "url": "https://www.nauticacadiz.com/adhesivos-y-selladores-embarcaciones/sikaflex-marino-291-sellador-poliuretano",
        "product": "291i", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },
    {
        "store": "Naval Chicolino 291i",
        "url": "https://navalchicolino.com/producto/sikaflex-marino-291-blanco-o-negro/",
        "product": "291i", "brand": "Sika", "category": "Marino",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },

    # ════════════════════════════════════════════
    # MARINO — Competencia
    # ════════════════════════════════════════════
    {
        "store": "Waveinn 3M5200",
        "url": "https://www.tradeinn.com/waveinn/es/3m-sellador-adhesivo-marino-5200/1288948/p",
        "product": "3M5200", "brand": "3M", "category": "Marino",
        "selectors": ["[data-testid='price']",".price","[itemprop='price']",".product-price"],
    },
    {
        "store": "Francobordo 3M5200",
        "url": "https://www.francobordo.com/3m-adhesivo-sellador-marine-5200-blanco-p-353215.html",
        "product": "3M5200", "brand": "3M", "category": "Marino",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "A.Alvarez 3M5200",
        "url": "https://www.a-alvarez.com/51842-sellador-adhesivo-3m-secado-rapido-5200",
        "product": "3M5200", "brand": "3M", "category": "Marino",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Waveinn 3M4200",
        "url": "https://www.tradeinn.com/waveinn/es/3m-sellador-adhesivo-marino-de-curado-rapido-4200/1288954/p",
        "product": "3M4200", "brand": "3M", "category": "Marino",
        "selectors": ["[data-testid='price']",".price","[itemprop='price']",".product-price"],
    },
    {
        "store": "Shop-SKS 3M4200",
        "url": "https://www.shop-sks.com/es/3M-Adhesivo-y-sellador-de-poliuretano-marino-4200-FC-negro-310-ml",
        "product": "3M4200", "brand": "3M", "category": "Marino",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Amazon BP795 marino",
        "url": "https://www.amazon.es/Bostik-Poliuretano-profesional-interiores-exteriores/dp/B09TTD2PMP",
        "product": "BP795", "brand": "Bostik", "category": "Marino",
        "selectors": [".a-price .a-offscreen","span.a-price-whole","#priceblock_ourprice"],
    },

    # ════════════════════════════════════════════
    # GENERAL — Sika
    # ════════════════════════════════════════════
    {
        "store": "Toolstock 621",
        "url": "https://www.toolstock.info/principal/10201-SIKAFLEX-621CARTCH300CM3-NEGRO",
        "product": "621", "brand": "Sika", "category": "General",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Plana Online 621",
        "url": "https://planaonline.com/es/nautica-y-marina/sikaflex-621.html",
        "product": "621", "brand": "Sika", "category": "General",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },

    # ════════════════════════════════════════════
    # GENERAL — Competencia
    # ════════════════════════════════════════════
    {
        "store": "Suministros Torras T939",
        "url": "https://www.suministrostorras.com/es/producto/83538/teroson-ms-939-gris-290ml-adhesivo-elastico-monocomponente-78846",
        "product": "T939", "brand": "Teroson", "category": "General",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Simor SS240",
        "url": "https://simor.es/producto/soudaseal-240-fc-290-ml/",
        "product": "SS240", "brand": "Soudal", "category": "General",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },
    {
        "store": "Mengual SS240",
        "url": "https://www.mengual.com/adhesivo-sellador-soudalseal-240fc-bolsa-de-600-ml",
        "product": "SS240", "brand": "Soudal", "category": "General",
        "selectors": ["[itemprop='price']",".price","[data-price]"],
    },
    {
        "store": "Ferreteria Esmas QT",
        "url": "https://www.ferreteriaesmas.com/adhesivos-de-montaje/117-polimero-adhesivo-fija-plus-turbo-quiadsa-8425608305791.html",
        "product": "QT", "brand": "Quiadsa", "category": "General",
        "selectors": ["[itemprop='price']",".price",".product-price"],
    },
    {
        "store": "Destornillate QT",
        "url": "https://www.destornillate.es/producto/quiadsa-adhesivo-sellador-fija-plus-turbo-blanco-290ml/",
        "product": "QT", "brand": "Quiadsa", "category": "General",
        "selectors": ["[itemprop='price']",".price",".woocommerce-Price-amount"],
    },
    {
        "store": "Carrefour SP101",
        "url": "https://www.carrefour.es/adhesivo-sellador-sp-101-gris-pattex/8410020407406/p",
        "product": "SP101", "brand": "Pattex", "category": "General",
        "selectors": ["[data-testid='product-price']",".product-price","[itemprop='price']"],
    },
    {
        "store": "Leroy Merlin SP101",
        "url": "https://www.leroymerlin.es/productos/adhesivo-sellador-polimero-pegador-multimaterial-cartucho-280-ml-blanco-sp101-pattex-16027200.html",
        "product": "SP101", "brand": "Pattex", "category": "General",
        "selectors": ["[data-testid='price']",".price__amount","[itemprop='price']"],
    },
    {
        "store": "Amazon SP101",
        "url": "https://www.amazon.es/Pattex-Sella-silicona-eficacia-fungicida/dp/B014WLHFL4",
        "product": "SP101", "brand": "Pattex", "category": "General",
        "selectors": [".a-price .a-offscreen","span.a-price-whole","#priceblock_ourprice"],
    },
    {
        "store": "Ventigo SS240",
        "url": "https://www.ventigo.es/es_ES/p/sellador-adhesivo-ms-polimero-gris-soudaseal-240fc-tubo-290ml-unidad/5881/",
        "product": "SS240", "brand": "Soudal", "category": "General",
        "selectors": ["[itemprop='price']",".price",".product-price"],
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
                    category=store_cfg.get("category", "General"),
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
            category=store_cfg.get("category", "General"),
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
