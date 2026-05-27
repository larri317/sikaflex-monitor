"""
Notificador por email (Gmail SMTP).
Envía un resumen diario con el Excel adjunto.
"""

import os
import smtplib
import logging
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get("EMAIL_USER", "")
SMTP_PASS = os.environ.get("EMAIL_PASS", "")
EMAIL_TO  = os.environ.get("EMAIL_TO", SMTP_USER)

EXCEL_PATH = Path(__file__).parent / "precios_sikaflex.xlsx"


def _build_html(summary: dict) -> str:
    today = summary["date"]
    results = summary["results"]
    alerts = summary["alerts"]
    daily_avgs = summary["daily_averages"]
    hist_avgs = summary["historical_averages"]
    product_names = summary.get("product_names", {})
    product_brands = summary.get("product_brands", {})

    BRAND_COLORS = {
        "Sika": "#E6B000", "Teroson": "#2563EB",
        "Soudal": "#16a34a", "Quiadsa": "#7C3AED", "Pattex": "#DC2626"
    }
    PRODUCT_COLORS = {
        "522": "#E6B000", "554": "#77BCB2", "621": "#333",
        "T930": "#2563EB", "T939": "#60A5FA",
        "SF45": "#16a34a", "SS240": "#4ADE80",
        "QT": "#7C3AED", "SP101": "#DC2626"
    }

    SIKA_PRODUCTS = ["522", "554", "621"]
    COMP_PRODUCTS = ["T930", "T939", "SF45", "SS240", "QT", "SP101"]
    ALL_PRODUCTS  = SIKA_PRODUCTS + COMP_PRODUCTS

    # ── Medias por producto ──────────────────────────────────
    def avg_row(product):
        d_avg = daily_avgs.get(product)
        h_avg = hist_avgs.get(product)
        name  = product_names.get(product, product)
        brand = product_brands.get(product, "")
        color = PRODUCT_COLORS.get(product, "#888")
        d_str = f"{d_avg:.2f} €" if d_avg else "—"
        h_str = f"{h_avg:.2f} €" if h_avg else "—"
        if d_avg and h_avg:
            pct = (d_avg - h_avg) / h_avg * 100
            trend = f"{'▲' if pct > 0 else '▼'} {abs(pct):.1f}%"
            trend_color = "#dc2626" if pct > 0 else "#16a34a"
        else:
            trend, trend_color = "—", "#888"
        return f"""
        <tr>
          <td style="padding:10px 14px">
            <span style="display:inline-block;background:{color};color:{'#000' if color in ['#E6B000','#4ADE80','#60A5FA'] else '#fff'};font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;font-family:monospace">{product}</span>
          </td>
          <td style="padding:10px 14px;font-weight:600">{name}</td>
          <td style="padding:10px 14px;font-size:11px;color:#888">{brand}</td>
          <td style="padding:10px 14px;font-weight:700;text-align:right;font-family:monospace">{d_str}</td>
          <td style="padding:10px 14px;text-align:right;color:#888;font-family:monospace">{h_str}</td>
          <td style="padding:10px 14px;text-align:right;font-weight:700;color:{trend_color}">{trend}</td>
        </tr>"""

    sika_rows = "".join(avg_row(p) for p in SIKA_PRODUCTS if daily_avgs.get(p))
    comp_rows = "".join(avg_row(p) for p in COMP_PRODUCTS if daily_avgs.get(p))

    # ── Precios por tienda ───────────────────────────────────
    sorted_results = sorted(results, key=lambda r: (product_brands.get(r.product,""), r.product, r.price))
    price_rows = ""
    for r in sorted_results:
        color = PRODUCT_COLORS.get(r.product, "#888")
        brand = product_brands.get(r.product, "")
        name  = product_names.get(r.product, r.product)
        price_rows += f"""
        <tr>
          <td style="padding:8px 14px">
            <span style="display:inline-block;background:{color};color:{'#000' if color in ['#E6B000','#4ADE80','#60A5FA'] else '#fff'};font-size:10px;font-weight:700;padding:2px 8px;border-radius:4px;font-family:monospace">{r.product}</span>
          </td>
          <td style="padding:8px 14px;font-size:11px;color:#888">{brand}</td>
          <td style="padding:8px 14px;font-weight:500">{r.store}</td>
          <td style="padding:8px 14px;font-weight:700;text-align:right;font-family:monospace">{r.price:.2f} €</td>
          <td style="padding:8px 14px;font-size:12px">
            <a href="{r.url}" style="color:#2563EB;text-decoration:none">Ver →</a>
          </td>
        </tr>"""

    # ── Alertas ──────────────────────────────────────────────
    if alerts:
        alert_items = ""
        for a in alerts:
            bg     = "#fff3f3" if a.pct_change > 0 else "#f0fff4"
            border = "#dc2626" if a.pct_change > 0 else "#16a34a"
            color  = "#dc2626" if a.pct_change > 0 else "#16a34a"
            arrow  = "▲" if a.pct_change > 0 else "▼"
            name   = product_names.get(a.product, a.product)
            alert_items += f"""
            <div style="background:{bg};border-left:4px solid {border};border-radius:6px;padding:14px 18px;margin-bottom:12px">
              <div style="font-size:15px;font-weight:700;color:{color}">{a.emoji} {a.alert_type} — {name}</div>
              <div style="margin-top:6px;font-size:13px"><b>{a.store}</b><br>
                {a.reference_price:.2f} € → <b>{a.current_price:.2f} €</b>
                <span style="color:{color};font-weight:700"> {arrow} {abs(a.pct_change):.1f}%</span>
                <span style="color:#888;font-size:11px"> (vs {a.reference_type})</span>
              </div>
              <a href="{a.url}" style="color:#2563EB;font-size:12px;display:inline-block;margin-top:6px">Ver producto →</a>
            </div>"""
        alerts_section = f"""
        <h2 style="color:#dc2626;margin:28px 0 14px;font-size:16px">
          ⚠️ Alertas de precio ({len(alerts)} detectada{'s' if len(alerts)>1 else ''})
        </h2>{alert_items}"""
    else:
        alerts_section = """
        <div style="background:#f0fff4;border-left:4px solid #16a34a;border-radius:6px;padding:14px 18px;margin:20px 0">
          ✅ <b>Sin alertas hoy.</b> Todos los precios dentro del rango normal.
        </div>"""

    # ── Sika vs Competencia ──────────────────────────────────
    sika_avg_all  = None
    comp_avg_all  = None
    sika_prices = [daily_avgs[p] for p in SIKA_PRODUCTS if daily_avgs.get(p)]
    comp_prices = [daily_avgs[p] for p in COMP_PRODUCTS if daily_avgs.get(p)]
    if sika_prices: sika_avg_all = sum(sika_prices)/len(sika_prices)
    if comp_prices: comp_avg_all = sum(comp_prices)/len(comp_prices)
    if sika_avg_all and comp_avg_all:
        diff = (sika_avg_all - comp_avg_all) / comp_avg_all * 100
        vs_text = f"{'▲' if diff>0 else '▼'} {abs(diff):.1f}% {'más caro' if diff>0 else 'más barato'} que la competencia"
        vs_color = "#dc2626" if diff > 0 else "#16a34a"
    else:
        vs_text, vs_color = "Sin datos suficientes", "#888"

    excel_note = "📎 <b>El Excel con el histórico completo y gráficos va adjunto a este email.</b>" if EXCEL_PATH.exists() else ""

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <body style="margin:0;padding:0;background:#f4f4f2;font-family:Inter,Arial,sans-serif;">
    <div style="max-width:680px;margin:30px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)">

      <!-- Header -->
      <div style="background:#000;padding:28px 32px;display:flex;align-items:center;gap:16px">
        <div style="width:44px;height:44px;background:#FCC500;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:22px">◆</div>
        <div>
          <div style="color:#FCC500;font-size:20px;font-weight:800;letter-spacing:2px">SIKA</div>
          <div style="color:rgba(255,255,255,.5);font-size:11px;letter-spacing:1.5px;text-transform:uppercase">Price Intelligence · {today}</div>
        </div>
      </div>

      <div style="padding:28px 32px">

        <!-- KPIs -->
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:24px">
          <div style="background:#f9f9f7;border-radius:10px;padding:16px;border-top:3px solid #FCC500">
            <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Media Sika hoy</div>
            <div style="font-size:22px;font-weight:800;font-family:monospace">{f'{sika_avg_all:.2f} €' if sika_avg_all else '—'}</div>
          </div>
          <div style="background:#f9f9f7;border-radius:10px;padding:16px;border-top:3px solid #77BCB2">
            <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Media Competencia</div>
            <div style="font-size:22px;font-weight:800;font-family:monospace">{f'{comp_avg_all:.2f} €' if comp_avg_all else '—'}</div>
          </div>
          <div style="background:#f9f9f7;border-radius:10px;padding:16px;border-top:3px solid {vs_color}">
            <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px">Sika vs Mercado</div>
            <div style="font-size:14px;font-weight:800;color:{vs_color}">{vs_text}</div>
          </div>
        </div>

        {alerts_section}

        <!-- Excel note -->
        {f'<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:8px;padding:12px 16px;margin-bottom:20px;font-size:13px;color:#92400e">{excel_note}</div>' if excel_note else ''}

        <!-- Sika products -->
        <h2 style="font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#888;margin:24px 0 12px">🟡 Productos Sika</h2>
        <table style="width:100%;border-collapse:collapse;border:1px solid #e8e8e4;border-radius:10px;overflow:hidden;margin-bottom:24px">
          <thead>
            <tr style="background:#f4f4f2">
              <th style="padding:10px 14px;text-align:left;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Ref</th>
              <th style="padding:10px 14px;text-align:left;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Producto</th>
              <th style="padding:10px 14px;text-align:left;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Marca</th>
              <th style="padding:10px 14px;text-align:right;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Media hoy</th>
              <th style="padding:10px 14px;text-align:right;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Media 7d</th>
              <th style="padding:10px 14px;text-align:right;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Var.</th>
            </tr>
          </thead>
          <tbody>{sika_rows}</tbody>
        </table>

        <!-- Competition products -->
        <h2 style="font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#888;margin:24px 0 12px">🔵 Competencia</h2>
        <table style="width:100%;border-collapse:collapse;border:1px solid #e8e8e4;border-radius:10px;overflow:hidden;margin-bottom:24px">
          <thead>
            <tr style="background:#f4f4f2">
              <th style="padding:10px 14px;text-align:left;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Ref</th>
              <th style="padding:10px 14px;text-align:left;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Producto</th>
              <th style="padding:10px 14px;text-align:left;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Marca</th>
              <th style="padding:10px 14px;text-align:right;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Media hoy</th>
              <th style="padding:10px 14px;text-align:right;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Media 7d</th>
              <th style="padding:10px 14px;text-align:right;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Var.</th>
            </tr>
          </thead>
          <tbody>{comp_rows}</tbody>
        </table>

        <!-- All prices -->
        <h2 style="font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#888;margin:24px 0 12px">🏪 Precios por tienda</h2>
        <table style="width:100%;border-collapse:collapse;border:1px solid #e8e8e4;border-radius:10px;overflow:hidden">
          <thead>
            <tr style="background:#f4f4f2">
              <th style="padding:8px 14px;text-align:left;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Ref</th>
              <th style="padding:8px 14px;text-align:left;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Marca</th>
              <th style="padding:8px 14px;text-align:left;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Tienda</th>
              <th style="padding:8px 14px;text-align:right;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Precio</th>
              <th style="padding:8px 14px;font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px">Link</th>
            </tr>
          </thead>
          <tbody>{price_rows}</tbody>
        </table>

      </div>

      <!-- Footer -->
      <div style="background:#f4f4f2;padding:16px 32px;text-align:center;color:#aaa;font-size:11px;border-top:1px solid #e8e8e4">
        Sika Price Monitor · Ejecutado automáticamente cada día a las 08:00 · {today}
      </div>
    </div>
    </body>
    </html>"""


def send_report(summary: dict, force_send: bool = False):
    alerts = summary["alerts"]

    if not alerts and not force_send:
        print("✅ Sin alertas. No se envía email.")
        return

    if not SMTP_USER or not SMTP_PASS:
        logger.error("❌ EMAIL_USER y EMAIL_PASS no configurados.")
        return

    subject_prefix = f"🔴 [{len(alerts)} alerta{'s' if len(alerts)>1 else ''}]" if alerts else "📊 Resumen diario"
    subject = f"{subject_prefix} · Sika Price Monitor · {summary['date']}"

    html_body = _build_html(summary)

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    recipients = [e.strip() for e in EMAIL_TO.split(",")]
msg["To"] = ", ".join(recipients)

    # Cuerpo HTML
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Adjuntar Excel si existe
    if EXCEL_PATH.exists():
        try:
            with open(EXCEL_PATH, "rb") as f:
                part = MIMEBase("application", "vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename=precios_sikaflex_{summary['date']}.xlsx"
                )
                msg.attach(part)
            print(f"📎 Excel adjuntado: precios_sikaflex_{summary['date']}.xlsx")
        except Exception as e:
            logger.warning(f"No se pudo adjuntar el Excel: {e}")
    else:
        logger.warning(f"Excel no encontrado en {EXCEL_PATH}")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, recipients, msg.as_string())
        print(f"📧 Email enviado a {EMAIL_TO} — Asunto: {subject}")
    except Exception as e:
        logger.error(f"❌ Error enviando email: {e}")
        raise
