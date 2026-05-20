# Earnings Calendar Dashboard — Setup completo

> Dashboard de earnings automático y gratuito. Se actualiza solo cada semana, vive en una URL pública de GitHub Pages, y puedes compartirlo en la comunidad como recurso fijo.

---

## Qué obtienes

Un archivo HTML autocontenido con:

- Headline con la temporada de earnings actual y KPIs (beats, misses, avg surprise)
- Countdown strip con las próximas 5 empresas en reportar
- Filtros por sector y búsqueda por ticker
- Cards por semana con: logo, ticker, fecha, AMC/BMO, EPS est, rev est, último surprise, Fwd P/E, precio actual
- Expandir cada card para ver "What to Watch" y riesgos clave
- Verde/rojo automático según si ya reportaron beat o miss
- Mobile-friendly, sin dependencias externas

Se regenera automáticamente cada lunes a las 6:00 UTC y cada viernes a las 20:00 UTC via GitHub Actions.

---

## Requisitos

- Cuenta de GitHub (gratis)
- API key de Financial Modeling Prep (plan gratuito suficiente)
- Python 3.11+ (solo para correrlo localmente)

---

## Paso 1 — Obtener API key gratuita de FMP

1. Ve a [financialmodelingprep.com](https://financialmodelingprep.com)
2. Crea cuenta gratuita
3. Ve a Dashboard → API Key
4. Copia tu API key (empieza por letras/números, ~32 caracteres)

El plan gratuito incluye el earnings calendar y datos de cotización. Suficiente para este dashboard.

---

## Paso 2 — Crear el repositorio en GitHub

1. Ve a [github.com/new](https://github.com/new)
2. Nombre del repo: `earnings-dashboard` (o el que quieras)
3. Visibilidad: **Public** (necesario para GitHub Pages gratis)
4. Haz click en **Create repository**

---

## Paso 3 — Subir los archivos

Tienes dos opciones:

### Opción A — Desde GitHub web (sin terminal)

1. En tu repo, haz click en **Add file → Upload files**
2. Sube `generate.py`
3. Crea la carpeta `.github/workflows/` manualmente:
   - Haz click en **Add file → Create new file**
   - Escribe el nombre: `.github/workflows/generate.yml`
   - Pega el contenido del archivo `generate.yml`
   - Haz commit

### Opción B — Desde terminal

```bash
git clone https://github.com/TU-USUARIO/earnings-dashboard.git
cd earnings-dashboard

# Copia los archivos generate.py y .github/workflows/generate.yml aquí
# Luego:
git add .
git commit -m "feat: add earnings dashboard generator"
git push
```

---

## Paso 4 — Añadir la API key como secreto

Nunca pongas la API key directamente en el código.

1. En tu repo, ve a **Settings → Secrets and variables → Actions**
2. Haz click en **New repository secret**
3. Name: `FMP_API_KEY`
4. Value: tu API key de FMP
5. Haz click en **Add secret**

---

## Paso 5 — Activar GitHub Pages

1. En tu repo, ve a **Settings → Pages**
2. Source: **GitHub Actions**
3. Guarda

---

## Paso 6 — Primera ejecución manual

El workflow se ejecuta automáticamente los lunes y viernes. Para ejecutarlo ahora:

1. Ve a **Actions** en tu repo
2. Haz click en **Generate Earnings Dashboard**
3. Haz click en **Run workflow → Run workflow**
4. Espera 2-3 minutos

Cuando termine, ve a **Settings → Pages** y verás la URL pública. Formato:
```
https://tu-usuario.github.io/earnings-dashboard/
```

---

## Personalización

### Cambiar qué empresas aparecen

El script fetch automaticamente las empresas con earnings en los próximos 90 días.
Para cambiar el número de días o el máximo de empresas, edita estas líneas en `generate.py`:

```python
DAYS_AHEAD = 90   # días hacia adelante
TOP_N      = 60   # máximo de empresas
```

### Añadir metadatos de empresas específicas

Para empresas que quieres con contexto personalizado, edita el diccionario `EXTRA_META` en `generate.py`:

```python
EXTRA_META = {
    "AAPL": {
        "theme": "Services margin expansion and AI device supercycle",
        "watch": [
            "iPhone 16 cycle sell-through vs analyst models",
            "Services revenue growth rate",
            ...
        ],
        "risks": ["China regulatory pressure", "Antitrust scrutiny"],
    },
    # Añade más empresas aquí
}
```

### Cambiar la frecuencia de actualización

Edita el cron en `.github/workflows/generate.yml`:

```yaml
schedule:
  - cron: '0 6 * * 1'   # Lunes 6:00 UTC
  - cron: '0 20 * * 5'  # Viernes 20:00 UTC
```

Formato: `minuto hora día-mes mes día-semana`

Para actualización diaria a las 7:00 UTC:
```yaml
  - cron: '0 7 * * *'
```

---

## Correrlo localmente

Si quieres probar el dashboard antes de subirlo o hacer cambios:

```bash
# Instalar dependencias
pip install requests yfinance

# Configurar API key
export FMP_API_KEY=tu-api-key-aqui

# Generar dashboard
python generate.py

# Abrir en el navegador
open index.html       # Mac
start index.html      # Windows
xdg-open index.html   # Linux
```

El archivo `index.html` generado es 100% autocontenido. Puedes abrirlo directamente en cualquier navegador sin servidor.

---

## Cómo compartirlo en la comunidad

Una vez desplegado, tienes una URL fija tipo:
```
https://tu-usuario.github.io/earnings-dashboard/
```

Esa URL siempre mostrará la versión más reciente. Cada vez que hay earnings relevantes puedes compartir esa URL en WhatsApp con contexto:

```
📅 Q2 2025 Earnings Season — dashboard actualizado

NVDA, MSFT, AAPL y 47 empresas más reportan las próximas semanas.
Cards con EPS est, surprise histórico, fwd P/E y qué vigilar.

→ [tu URL de GitHub Pages]
```

---

## Estructura de archivos

```
earnings-dashboard/
├── generate.py              ← script principal
├── index.html               ← dashboard generado (auto-actualizado)
└── .github/
    └── workflows/
        └── generate.yml     ← automatización semanal
```

---

## Solución de problemas

**El workflow falla con error 401**
→ Tu FMP_API_KEY no está configurada correctamente. Revisa Settings → Secrets.

**El workflow falla con "No data returned"**
→ El plan gratuito de FMP tiene límite de llamadas. Espera 24h o actualiza el plan.

**GitHub Pages muestra 404**
→ Asegúrate de que el repo es público y que Pages está configurado como "GitHub Actions" source.

**Los logos no aparecen**
→ Normal para empresas pequeñas o sin dominio web estándar. Se muestra el fallback con las iniciales del ticker.

---

## Recursos

- Financial Modeling Prep API docs: [site.financialmodelingprep.com/developer/docs](https://site.financialmodelingprep.com/developer/docs)
- GitHub Pages docs: [docs.github.com/pages](https://docs.github.com/pages)
- GitHub Actions cron syntax: [crontab.guru](https://crontab.guru)