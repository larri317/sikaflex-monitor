# 📊 Sikaflex Price Monitor

Agente que monitorea diariamente los precios de **Sikaflex 522** y **Sikaflex 621 Purform**
en tiendas online españolas, calcula medias y te alerta por email si alguna tienda
sube el precio más de un **10%**.

---

## 🏗️ Arquitectura

```
GitHub Actions (cron diario 08:00)
       │
       ▼
  src/main.py
  ├── scraper.py   → Descarga precios de cada tienda
  ├── database.py  → Guarda/lee data/prices.csv
  ├── alerts.py    → Detecta variaciones > 10%
  └── notifier.py  → Envía email HTML con resumen y alertas
```

El historial de precios se guarda como `data/prices.csv` directamente en el repositorio.
GitHub Actions hace un `git commit` automático cada día con los nuevos datos.

---

## 🚀 Puesta en marcha (paso a paso)

### 1. Crear el repositorio en GitHub

```bash
# En tu máquina local:
cd sikaflex-monitor
git init
git add .
git commit -m "🚀 Primer commit — Sikaflex Price Monitor"

# Crea un repo en github.com y luego:
git remote add origin https://github.com/TU_USUARIO/sikaflex-monitor.git
git push -u origin main
```

### 2. Configurar el email (Gmail)

El agente usa Gmail SMTP. Necesitas una **App Password** (no tu contraseña normal).

**Cómo generar la App Password de Gmail:**
1. Ve a [myaccount.google.com/security](https://myaccount.google.com/security)
2. Activa la **verificación en 2 pasos** (si no la tienes)
3. Busca "Contraseñas de aplicaciones" → Crear nueva → ponle nombre "Sikaflex Monitor"
4. Google te dará una contraseña de 16 caracteres → **cópiala**

### 3. Añadir los Secrets en GitHub

En tu repositorio GitHub:
- Ve a `Settings → Secrets and variables → Actions → New repository secret`

| Secret       | Valor                                      |
|--------------|--------------------------------------------|
| `EMAIL_USER` | tu dirección Gmail (p.ej. `tu@gmail.com`)  |
| `EMAIL_PASS` | la App Password de 16 caracteres           |
| `EMAIL_TO`   | email donde quieres recibir las alertas    |

### 4. ¡Listo! El agente se ejecuta solo

- **Automáticamente** cada día a las **08:00** (hora Madrid)
- **Manualmente** desde `Actions → Sikaflex Price Monitor → Run workflow`
  - Puedes marcar "Enviar email aunque no haya alertas" para recibir el resumen diario completo

---

## 📧 Qué recibirás por email

### Si hay alertas (precio subido >10%):
```
🔴 [1 alerta] · Monitor Sikaflex · 2025-06-01
```
- Detalle de qué tienda subió el precio
- Cuánto subió y respecto a qué referencia
- Enlace directo al producto

### Resumen diario (con --force-email):
- Media de precios del día por producto
- Comparación con media de los últimos 7 días
- Tabla con precios de todas las tiendas

---

## ➕ Añadir nuevas tiendas

Edita `src/scraper.py` y añade una entrada al array `STORES`:

```python
{
    "store": "Nombre de la Tienda",
    "url": "https://www.tienda.com/producto-sikaflex-522",
    "product": "522",   # o "621"
    "selectors": [
        "span.price",           # selector CSS principal
        "[itemprop='price']",   # alternativa 1
        ".product-price",       # alternativa 2
    ],
},
```

**Cómo encontrar el selector correcto:**
1. Abre la página del producto en Chrome
2. Clic derecho sobre el precio → "Inspeccionar"
3. Copia el selector CSS del elemento que muestra el precio
4. Añádelo como primer selector en la lista

---

## 🔧 Ejecución local (para pruebas)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar (scraping real + detección + email si hay alertas)
python src/main.py

# Ejecutar sin guardar ni enviar email
python src/main.py --dry-run

# Ejecutar y enviar email aunque no haya alertas
python src/main.py --force-email
```

Para ejecutar localmente con email, crea un archivo `.env` (no lo subas a Git):
```
EMAIL_USER=tu@gmail.com
EMAIL_PASS=abcd efgh ijkl mnop
EMAIL_TO=destino@email.com
```
Y cárgalo antes de ejecutar:
```bash
export $(cat .env | xargs) && python src/main.py
```

---

## 📁 Estructura del proyecto

```
sikaflex-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml      ← Scheduler de GitHub Actions
├── data/
│   └── prices.csv           ← Base de datos histórica (se actualiza sola)
├── src/
│   ├── main.py              ← Orquestador principal
│   ├── scraper.py           ← Descarga precios de tiendas
│   ├── database.py          ← Lectura/escritura del CSV
│   ├── alerts.py            ← Detección de variaciones >10%
│   └── notifier.py          ← Envío de email HTML
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚠️ Notas importantes

- **Legalidad**: el scraping de precios públicos para uso personal es generalmente aceptable,
  pero revisa los términos de servicio de cada tienda.
- **Bloqueos**: algunas tiendas pueden bloquear el scraper con el tiempo. Si falla una,
  actualiza los selectores CSS en `scraper.py`.
- **Primer día**: el primer día no habrá histórico, así que no se generarán alertas comparativas.
  A partir del segundo día ya funciona la detección.
