"""
Sikaflex Price Monitor — Punto de entrada principal.
"""

import sys
import logging
import argparse
from datetime import date

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from scraper import scrape_all
from database import save_prices, get_daily_average
from alerts import detect_alerts, build_daily_summary
from notifier import send_report
from generate_excel import generate_excel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def main():
    parser = argparse.ArgumentParser(description="Sikaflex Price Monitor")
    parser.add_argument("--force-email", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    today = date.today()
    print(f"\n{'='*55}")
    print(f"  🔍 Sikaflex Price Monitor · {today.isoformat()}")
    print(f"{'='*55}\n")

    # 1. Scraping
    print("📡 Paso 1/5 — Scraping de tiendas...")
    results = scrape_all(delay_seconds=2.0)
    if not results:
        logger.error("❌ No se obtuvieron precios.")
        sys.exit(1)
    print(f"   ✓ {len(results)} precios obtenidos\n")

    # 2. Guardar en CSV
    print("💾 Paso 2/5 — Guardando en base de datos...")
    if not args.dry_run:
        save_prices(results, run_date=today)
    else:
        print("   [dry-run] Guardado omitido")
    print()

    # 3. Generar Excel
    print("📊 Paso 3/5 — Generando Excel...")
    if not args.dry_run:
        generate_excel()
    else:
        print("   [dry-run] Excel omitido")
    print()

    # 4. Detectar alertas
    print("🔎 Paso 4/5 — Detectando alertas de precio...")
    alerts = detect_alerts(results)
    if alerts:
        print(f"   ⚠️  {len(alerts)} alerta(s):")
        for a in alerts:
            print(f"      {a.summary}")
    else:
        print("   ✅ Sin alertas.")
    print()

    # 5. Email
    print("📧 Paso 5/5 — Enviando notificación...")
    summary = build_daily_summary(results, alerts, today=today)
    if not args.dry_run:
        send_report(summary, force_send=args.force_email)
    else:
        print("   [dry-run] Email omitido")

    print(f"\n{'='*55}")
    print(f"  ✅ Ejecución completada")
    print(f"  Tiendas analizadas : {len(results)}")
    print(f"  Alertas detectadas : {len(alerts)}")
    for product in ["522", "554", "621"]:
        avg = get_daily_average(product, today)
        if avg:
            print(f"  Media Sikaflex {product}  : {avg:.2f} €")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    main()
