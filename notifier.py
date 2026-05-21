"""
Notificador por email (Gmail SMTP).
Envía un resumen diario y alertas de precio.
"""

import os
import smtplib
import logging
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ─── Configuración (se lee de variables de entorno) ───────────
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get("EMAIL_USER", "")          # tu Gmail
SMTP_PASS = os.environ.get("EMAIL_PASS", "")          # app password de Google
EMAIL_TO   = os.environ.get("EMAIL_TO", SMTP_USER)    # destinatario


def _build_html(summary: dict) -> str:
    today = summary["date"]
    results = summary["results"]
    alerts = summary["alerts"]
    daily_avgs = summary["daily_averages"]
    hist_avgs = summary["historical_averages"]

    # ── Tabla de medias ──────────────────────────────────────
    avg_rows = ""
    for product in ["522", "621"]:
        d_avg = daily_avgs.get(product)
        h_avg = hist_avgs.get(product)
        d_str = f"{d_avg:.2f} €" if d_avg else "—"
        h_str = f"{h_avg:.2f} €" if h_avg else "—"

        if d_avg and h_avg:
            pct = (d_avg - h_avg) / h_avg * 100
            trend = f"{'▲' if pct > 0 else '▼'} {abs(pct):.1f}%"
            trend_color = "#e74c3c" if pct > 0 else "#27ae60"
        else:
            trend = "—"
            trend_color = "#888"

        avg_rows += f"""
        <tr>
          <td style="padding:10px 14px;font-weight:700;">Sikaflex {product}</td>
          <td style="padding:10px 14px;text-align:center;">{d_str}</td>
          <td style="padding:10px 14px;text-align:center;">{h_str}</td>
          <td style="padding:10px 14px;text-align:center;color:{trend_color};font-weight:700;">{trend}</td>
        </tr>"""

    # ── Tabla de precios por tienda ──────────────────────────
    price_rows = ""
    for r in sorted(results, key=lambda x: (x.product, x.price)):
        price_rows += f"""
        <tr>
          <td style="padding:8px 14px;">Sikaflex {r.product}</td>
          <td style="padding:8px 14px;">{r.store}</td>
          <td style="padding:8px 14px;font-weight:700;text-align:right;">{r.price:.2f} €</td>
          <td style="padding:8px 14px;font-size:12px;color:#666;">
            <a href="{r.url}" style="color:#3498db;">Ver producto</a>
          </td>
        </tr>"""

    # ── Sección de alertas ───────────────────────────────────
    if alerts:
        alert_items = ""
        for a in alerts:
            bg = "#fff3f3" if a.pct_change > 0 else "#f3fff6"
            border = "#e74c3c" if a.pct_change > 0 else "#27ae60"
            color = "#e74c3c" if a.pct_change > 0 else "#27ae60"
            arrow = "▲" if a.pct_change > 0 else "▼"
            alert_items += f"""
            <div style="background:{bg};border-left:4px solid {border};
                        border-radius:6px;padding:14px 18px;margin-bottom:12px;">
              <div style="font-size:16px;font-weight:700;color:{color};">
                {a.emoji} {a.alert_type} — Sikaflex {a.product}
              </div>
              <div style="margin-top:6px;font-size:14px;">
                <b>{a.store}</b><br>
                {a.reference_price:.2f} € → <b>{a.current_price:.2f} €</b>
                <span style="color:{color};font-weight:700;"> {arrow} {abs(a.pct_change):.1f}%</span>
                <span style="color:#888;font-size:12px;"> (vs {a.reference_type})</span>
              </div>
              <div style="margin-top:6px;">
                <a href="{a.url}" style="color:#3498db;font-size:13px;">Ver en la tienda →</a>
              </div>
            </div>"""

        alerts_section = f"""
        <h2 style="color:#e74c3c;margin:28px 0 14px;">
          ⚠️ Alertas de precio ({len(alerts)} detectada{'s' if len(alerts)>1 else ''})
        </h2>
        {alert_items}"""
    else:
        alerts_section = """
        <div style="background:#f3fff6;border-left:4px solid #27ae60;
                    border-radius:6px;padding:14px 18px;margin:28px 0;">
          ✅ <b>Sin alertas hoy.</b> Todos los precios están dentro del rango normal.
        </div>"""

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,sans-serif;">
    <div style="max-width:640px;margin:30px auto;background:#fff;
                border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);">

      <!-- Header -->
      <div style="background:linear-gradient(135deg,#e63b2e,#c0281c);
                  padding:28px 32px;text-align:center;">
        <div style="color:#fff;font-size:22px;font-weight:700;letter-spacing:-0.5px;">
          📊 Monitor de Precios Sikaflex
        </div>
        <div style="color:rgba(255,255,255,.8);font-size:14px;margin-top:6px;">
          Informe diario · {today}
        </div>
      </div>

      <div style="padding:28px 32px;">

        <!-- Estadísticas rápidas -->
        <div style="display:flex;gap:12px;margin-bottom:24px;">
          <div style="flex:1;background:#f8f9fa;border-radius:8px;padding:16px;text-align:center;">
            <div style="font-size:28px;font-weight:700;color:#2c3e50;">
              {summary['stores_scraped']}
            </div>
            <div style="color:#888;font-size:12px;margin-top:4px;">Tiendas analizadas</div>
          </div>
          <div style="flex:1;background:#f8f9fa;border-radius:8px;padding:16px;text-align:center;">
            <div style="font-size:28px;font-weight:700;
                        color:{'#e74c3c' if summary['alerts_count'] > 0 else '#27ae60'};">
              {summary['alerts_count']}
            </div>
            <div style="color:#888;font-size:12px;margin-top:4px;">Alertas detectadas</div>
          </div>
        </div>

        <!-- Media de precios -->
        <h2 style="color:#2c3e50;margin:0 0 12px;font-size:16px;">
          📈 Media de precios del día
        </h2>
        <table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;
                      border:1px solid #eee;margin-bottom:24px;">
          <thead>
            <tr style="background:#f8f9fa;">
              <th style="padding:10px 14px;text-align:left;font-size:13px;color:#666;">Producto</th>
              <th style="padding:10px 14px;text-align:center;font-size:13px;color:#666;">Media hoy</th>
              <th style="padding:10px 14px;text-align:center;font-size:13px;color:#666;">Media 7 días</th>
              <th style="padding:10px 14px;text-align:center;font-size:13px;color:#666;">Variación</th>
            </tr>
          </thead>
          <tbody>{avg_rows}</tbody>
        </table>

        <!-- Alertas -->
        {alerts_section}

        <!-- Precios por tienda -->
        <h2 style="color:#2c3e50;margin:28px 0 12px;font-size:16px;">
          🏪 Precios por tienda
        </h2>
        <table style="width:100%;border-collapse:collapse;border:1px solid #eee;
                      border-radius:8px;overflow:hidden;">
          <thead>
            <tr style="background:#f8f9fa;">
              <th style="padding:8px 14px;text-align:left;font-size:13px;color:#666;">Producto</th>
              <th style="padding:8px 14px;text-align:left;font-size:13px;color:#666;">Tienda</th>
              <th style="padding:8px 14px;text-align:right;font-size:13px;color:#666;">Precio</th>
              <th style="padding:8px 14px;font-size:13px;color:#666;">Enlace</th>
            </tr>
          </thead>
          <tbody>{price_rows}</tbody>
        </table>

      </div>

      <!-- Footer -->
      <div style="background:#f8f9fa;padding:16px 32px;text-align:center;
                  color:#aaa;font-size:12px;border-top:1px solid #eee;">
        Sikaflex Price Monitor · Ejecutado automáticamente cada día a las 08:00
      </div>
    </div>
    </body>
    </html>"""


def send_report(summary: dict, force_send: bool = False):
    """
    Envía el email de informe diario.
    Solo envía si hay alertas, a menos que force_send=True.
    """
    alerts = summary["alerts"]

    if not alerts and not force_send:
        print("✅ Sin alertas hoy. No se envía email (usa force_send=True para el resumen diario completo).")
        return

    if not SMTP_USER or not SMTP_PASS:
        logger.error("❌ EMAIL_USER y EMAIL_PASS no configurados. Revisa las variables de entorno.")
        return

    subject_prefix = f"🔴 [{len(alerts)} alerta{'s' if len(alerts)>1 else ''}]" if alerts else "📊 Resumen diario"
    subject = f"{subject_prefix} · Monitor Sikaflex · {summary['date']}"

    html_body = _build_html(summary)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())
        print(f"📧 Email enviado a {EMAIL_TO} — Asunto: {subject}")
    except Exception as e:
        logger.error(f"❌ Error enviando email: {e}")
        raise
