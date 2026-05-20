# Claude Enterprise — Trading Hub

> Dashboard de trading completo y gratuito. Earnings calendar + day trading dashboard en un solo repo. Se actualiza automáticamente, vive en una URL pública de GitHub Pages y está optimizado para la apertura de NASDAQ a las 15:30 CET.

---

## Qué obtienes

### Landing page (raíz)
- Reloj en tiempo real con hora CET, hora ET y cuenta atrás hasta las 15:30 CET
- Estado del mercado live (Pre-market / Abierto / After-hours / Cerrado)
- Checklist pre-apertura de 7 puntos para tu rutina diaria
- Links rápidos a TradingView, CME futuros, calendario macro, VIX, etc.

### Day Trading Dashboard (`/trading`)
- Índices y ETFs: NASDAQ 100, S&P 500, VIX, QQQ, SPY
- Watchlist NASDAQ: NVDA, GOOGL, MSFT, AAPL, META, AMZN, TSLA, AMD, PLTR y más
- Cada fila expandible con niveles de scalping, setup VWAP, catalizadores y notas de opciones
- Pre-market price y cambio para cada ticker
- Crypto: BTC, ETH, ZEC, SOL, XRP, AVAX, LINK, ARB, MATIC, SUI, DOGE con cambios 1h/24h/7d
- Global crypto: dominancia BTC/ETH, market cap total, volumen 24h
- Calendario macro semanal con impacto y reglas de gestión de riesgo para scalping
- Se actualiza L-V a las 13:00 UTC (15:00 CET, antes de apertura) y 21:30 UTC

### Earnings Calendar (`/earnings`)
- KPIs de temporada: beats, misses, avg surprise
- Countdown con las próximas 5 empresas en reportar
- Cards por semana: EPS est, rev est, último surprise, Fwd P/E, precio actual
- Expandir cada card para ver "What to Watch" y riesgos clave
- Verde/rojo automático según beat o miss
- Se actualiza L y V a las 06:00 y 20:00 UTC

---

## Estructura del repo

```
earnings-dashboard/
├── index.html                     ← landing page (raíz)
├── trading/
│   ├── generate.py                ← script day trading dashboard
│   └── index.html                 ← generado automáticamente
├── earnings/
│   ├── generate.py                ← script earnings calendar
│   └── index.html                 ← generado automáticamente
└── .github/
    └── workflows/
        ├── trading.yml            ← cron L-V 13:00 y 21:30 UTC
        └── earnings.yml           ← cron L y V 06:00 y 20:00 UTC
```

---

## Requisitos

- Cuenta de GitHub (gratis)
- API key de Financial Modeling Prep — solo para earnings (plan gratuito suficiente)
- Day trading dashboard usa Yahoo Finance y CoinGecko — sin API key necesaria
- Python 3.11+ para correrlo localmente

---

## Setup inicial

### Paso 1 — API key de FMP (solo para earnings)

1. Ve a [financialmodelingprep.com](https://financialmodelingprep.com)
2. Crea cuenta gratuita → Dashboard → API Key
3. Copia tu API key (~32 caracteres)

### Paso 2 — Añadir el secreto en GitHub

1. En tu repo → **Settings → Secrets and variables → Actions**
2. **New repository secret**
3. Name: `FMP_API_KEY` · Value: tu API key
4. **Add secret**

### Paso 3 — Activar GitHub Pages

1. En tu repo → **Settings → Pages**
2. Source: **GitHub Actions**
3. Guarda

### Paso 4 — Primera ejecución manual

Ejecuta cada workflow por separado la primera vez:

1. Ve a **Actions** en tu repo
2. Selecciona **Generate Trading Dashboard** → **Run workflow**
3. Espera 2-3 minutos
4. Repite con **Generate Earnings Dashboard**

Tu URL pública:
```
https://tu-usuario.github.io/earnings-dashboard/
```

---

## Correrlo localmente

```bash
# Instalar dependencias
pip install requests yfinance

# Trading dashboard (sin API key)
cd trading
python generate.py
open index.html

# Earnings dashboard (requiere FMP key)
cd earnings
export FMP_API_KEY=tu-api-key-aqui
python generate.py
open index.html
```

---

## Personalización

### Añadir o quitar stocks del trading dashboard

Edita la lista `STOCKS` en `trading/generate.py`:

```python
STOCKS = [
    {"ticker": "NVDA",  "name": "NVIDIA",    "sector": "AI/Semis"},
    {"ticker": "GOOGL", "name": "Alphabet",  "sector": "Mega Cap"},
    # Añade o quita aquí
]
```

### Añadir contexto de scalping por ticker

Edita `SCALP_META` en `trading/generate.py`:

```python
SCALP_META = {
    "NVDA": {
        "vwap_note": "Respeta VWAP con fuerza. Pre-market gaps frecuentes.",
        "key_levels": ["Soporte en redondos ($100, $110...)", "ATH como resistencia"],
        "catalysts":  ["Export controls news", "Hyperscaler capex"],
        "avg_range":  "4-8% daily range en días de noticias",
        "options_note": "Alta IV en earnings. Gamma squeeze frecuente.",
    },
    # Añade más tickers aquí
}
```

### Añadir contexto de earnings por empresa

Edita `EXTRA_META` en `earnings/generate.py`:

```python
EXTRA_META = {
    "AAPL": {
        "theme": "Services margin expansion and AI device supercycle",
        "watch": [
            "iPhone 16 cycle sell-through vs analyst models",
            "Services revenue growth rate",
        ],
        "risks": ["China regulatory pressure", "Antitrust scrutiny"],
    },
}
```

### Cambiar frecuencia de actualización

`trading/.github/workflows/trading.yml`:
```yaml
schedule:
  - cron: '0 13 * * 1-5'   # L-V 13:00 UTC (15:00 CET)
  - cron: '30 21 * * 1-5'  # L-V 21:30 UTC (after close)
```

`earnings/.github/workflows/earnings.yml`:
```yaml
schedule:
  - cron: '0 6 * * 1'    # Lunes 6:00 UTC
  - cron: '0 20 * * 5'   # Viernes 20:00 UTC
```

Generador de cron: [crontab.guru](https://crontab.guru)

---

## Cómo compartirlo en la comunidad

URL fija siempre actualizada:
```
https://tu-usuario.github.io/earnings-dashboard/
```

Formato para WhatsApp:

```
📊 Trading Hub actualizado — apertura NASDAQ 15:30

Dashboard con NVDA, GOOGL, MSFT y crypto en tiempo real.
Checklist pre-apertura, niveles de scalping y earnings de la semana.

→ https://tu-usuario.github.io/earnings-dashboard/
```

---

## Solución de problemas

**El workflow de trading falla**
→ Yahoo Finance y CoinGecko son gratuitos pero tienen rate limits. Espera 30 minutos y reintenta.

**El workflow de earnings falla con 401**
→ `FMP_API_KEY` no configurada. Revisa Settings → Secrets and variables → Actions.

**El workflow de earnings falla con "No data returned"**
→ Límite del plan gratuito de FMP. Espera 24h.

**GitHub Pages muestra 404 en `/trading` o `/earnings`**
→ Los `index.html` de cada subcarpeta se generan cuando el workflow corre. Ejecuta ambos workflows manualmente la primera vez.

**Los logos de stocks no aparecen**
→ Clearbit logo API tiene límites. Normal para empresas pequeñas. Muestra iniciales del ticker como fallback.

**El reloj de la landing page muestra hora incorrecta**
→ El reloj usa la zona horaria del navegador para CET. Si estás fuera de España ajusta la zona en el `index.html`.

---

## Recursos

- Financial Modeling Prep API: [site.financialmodelingprep.com/developer/docs](https://site.financialmodelingprep.com/developer/docs)
- CoinGecko API: [docs.coingecko.com](https://docs.coingecko.com)
- GitHub Pages: [docs.github.com/pages](https://docs.github.com/pages)
- GitHub Actions cron: [crontab.guru](https://crontab.guru)
- Comunidad: Claude Enterprise (WhatsApp)