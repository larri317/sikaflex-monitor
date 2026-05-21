"""
Sikaflex Price Monitor — Punto de entrada principal.
Orquesta: scraping → guardado → detección → notificación.

Uso:
    python src/main.py                  # ejecución normal
    python src/main.py --force-email    # envía email aunque no haya alertas
    python src/main.py --dry-run        # scraping real pero sin guardar ni enviar
"""

import sys
import logging
import argparse
from datetime import date

# Añadir src/ al path para importar módulos locales
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from scraper import scrape_all
from database import save_prices, get_daily_average
from alerts import detect_alerts, build_daily_summary
from notifier import send_report

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def main():
    parser = argparse.ArgumentParser(description="Sikaflex Price Monitor")
    parser.add_argument("--force-email", action="store_true",
                        help="Envía el email aunque no haya alertas")
    parser.add_argument("--dry-run", action="store_true",
                        help="Scraping real pero sin guardar ni enviar email")
    args = parser.parse_args()

    today = date.today()
    print(f"\n{'='*55}")
    print(f"  🔍 Sikaflex Price Monitor · {today.isoformat()}")
    print(f"{'='*55}\n")

    # ── 1. Scraping ───────────────────────────────────────────
    print("📡 Paso 1/4 — Scraping de tiendas...")
    results = scrape_all(delay_seconds=2.0)

    if not results:
        logger.error("❌ No se obtuvieron precios. Revisa las URLs de las tiendas.")
        sys.exit(1)

    print(f"   ✓ {len(results)} precios obtenidos\n")

    # ── 2. Guardar en CSV ─────────────────────────────────────
    print("💾 Paso 2/4 — Guardando en base de datos...")
    if not args.dry_run:
        save_prices(results, run_date=today)
    else:
        print("   [dry-run] Guardado omitido")
    print()

    # ── 3. Detectar alertas ───────────────────────────────────
    print("🔎 Paso 3/4 — Detectando alertas de precio...")
    alerts = detect_alerts(results)

    if alerts:
        print(f"   ⚠️  {len(alerts)} alerta(s) detectada(s):")
        for a in alerts:
            print(f"      {a.summary}")
    else:
        print("   ✅ Sin alertas. Todos los precios en rango normal.")
    print()

    # ── 4. Notificación por email ─────────────────────────────
    print("📧 Paso 4/4 — Enviando notificación...")
    summary = build_daily_summary(results, alerts, today=today)

    if not args.dry_run:
        send_report(summary, force_send=args.force_email)
    else:
        print("   [dry-run] Email omitido")

    # ── Resumen final ─────────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  ✅ Ejecución completada")
    print(f"  Tiendas analizadas : {len(results)}")
    print(f"  Alertas detectadas : {len(alerts)}")
    for product in ["522", "621"]:
        avg = get_daily_average(product, today)
        if avg:
            print(f"  Media Sikaflex {product}  : {avg:.2f} €")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
