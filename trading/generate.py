#!/usr/bin/env python3
"""
Day Trading Dashboard Generator
Fuentes: Yahoo Finance (indices, futuros, stocks), CoinGecko (crypto), FMP (noticias)
"""

import json
import os
import re
import sys
import datetime
import urllib.request
import urllib.parse
import time
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "index.html"
FMP_API_KEY = os.getenv("FMP_API_KEY", "")

# ─── WATCHLISTS ───────────────────────────────────────────────

INDICES = [
    {"ticker": "^NDX",  "name": "NASDAQ 100", "short": "NQ"},
    {"ticker": "^GSPC", "name": "S&P 500",    "short": "SPX"},
    {"ticker": "^VIX",  "name": "VIX",        "short": "VIX"},
    {"ticker": "QQQ",   "name": "QQQ ETF",    "short": "QQQ"},
    {"ticker": "SPY",   "name": "SPY ETF",    "short": "SPY"},
]

FUTURES = [
    {"ticker": "NQ=F",  "name": "NASDAQ 100 Fut", "short": "NQ Fut"},
    {"ticker": "ES=F",  "name": "S&P 500 Fut",    "short": "ES Fut"},
    {"ticker": "YM=F",  "name": "Dow Jones Fut",  "short": "YM Fut"},
    {"ticker": "RTY=F", "name": "Russell 2000",   "short": "RTY"},
    {"ticker": "GC=F",  "name": "Gold",           "short": "Gold"},
    {"ticker": "CL=F",  "name": "Crude Oil",      "short": "Oil"},
]

STOCKS = [
    {"ticker": "NVDA",  "name": "NVIDIA",        "sector": "AI/Semis"},
    {"ticker": "GOOGL", "name": "Alphabet",      "sector": "Mega Cap"},
    {"ticker": "MSFT",  "name": "Microsoft",     "sector": "Mega Cap"},
    {"ticker": "AAPL",  "name": "Apple",         "sector": "Mega Cap"},
    {"ticker": "META",  "name": "Meta",          "sector": "Mega Cap"},
    {"ticker": "AMZN",  "name": "Amazon",        "sector": "Mega Cap"},
    {"ticker": "TSLA",  "name": "Tesla",         "sector": "EV/Tech"},
    {"ticker": "AMD",   "name": "AMD",           "sector": "AI/Semis"},
    {"ticker": "PLTR",  "name": "Palantir",      "sector": "AI/Data"},
    {"ticker": "MU",    "name": "Micron",        "sector": "Semis"},
    {"ticker": "AVGO",  "name": "Broadcom",      "sector": "AI/Semis"},
    {"ticker": "NFLX",  "name": "Netflix",       "sector": "Streaming"},
    {"ticker": "SMCI",  "name": "Super Micro",   "sector": "AI Infra"},
    {"ticker": "ARM",   "name": "Arm Holdings",  "sector": "AI/Semis"},
    {"ticker": "MSTR",  "name": "MicroStrategy", "sector": "BTC Proxy"},
]

CRYPTO_IDS = [
    {"id": "bitcoin",       "ticker": "BTC",  "name": "Bitcoin"},
    {"id": "ethereum",      "ticker": "ETH",  "name": "Ethereum"},
    {"id": "zcash",         "ticker": "ZEC",  "name": "Zcash"},
    {"id": "solana",        "ticker": "SOL",  "name": "Solana"},
    {"id": "ripple",        "ticker": "XRP",  "name": "XRP"},
    {"id": "avalanche-2",   "ticker": "AVAX", "name": "Avalanche"},
    {"id": "chainlink",     "ticker": "LINK", "name": "Chainlink"},
    {"id": "arbitrum",      "ticker": "ARB",  "name": "Arbitrum"},
    {"id": "matic-network", "ticker": "MATIC","name": "Polygon"},
    {"id": "sui",           "ticker": "SUI",  "name": "Sui"},
    {"id": "pepe",          "ticker": "PEPE", "name": "Pepe"},
    {"id": "dogecoin",      "ticker": "DOGE", "name": "Dogecoin"},
]

NEWS_TICKERS  = {"NVDA","MSFT","AAPL","GOOGL","META","AMZN","TSLA","AMD","SPY","QQQ"}
NEWS_KEYWORDS = ["nasdaq","s&p","fed","rate","inflation","gdp","jobs","payroll",
                 "nvidia","microsoft","apple","google","meta","amazon","tesla","amd",
                 "interest rate","fomc","treasury","earnings","market"]

SCALP_META = {
    "NVDA": {
        "vwap_note": "Respeta VWAP con fuerza. Pre-market gaps frecuentes en noticias de IA.",
        "key_levels": ["Soporte psicologico en redondos ($100, $110, $120...)", "ATH como resistencia clave"],
        "catalysts": ["Comentarios de hyperscalers", "Noticias de export controls", "Datos de chips"],
        "avg_range": "4-8% daily range en dias de noticias",
        "options_note": "Alta IV en earnings. Gamma squeeze frecuente.",
    },
    "GOOGL": {
        "vwap_note": "Movimientos mas lentos que NVDA. Buen seguimiento de tendencia intraday.",
        "key_levels": ["Soporte en 8-EMA en grafico 15min", "Gap fills frecuentes"],
        "catalysts": ["DOJ antitrust news", "AI announcements", "Cloud metrics"],
        "avg_range": "2-4% daily range",
        "options_note": "Spread mas amplio que NVDA. Mejor operar en el subyacente.",
    },
    "MSFT": {
        "vwap_note": "El mas estable de los mega caps. Rebotes en VWAP muy limpios.",
        "key_levels": ["200-day MA como soporte mayor", "Niveles de earnings anteriores"],
        "catalysts": ["Azure cloud numbers", "Copilot adoption news", "OpenAI developments"],
        "avg_range": "1.5-3% daily range",
        "options_note": "IV relativamente baja fuera de earnings. Bueno para spreads.",
    },
    "TSLA": {
        "vwap_note": "Alta volatilidad. Fakeouts frecuentes en VWAP. Confirmar con volumen.",
        "key_levels": ["$200, $250, $300 niveles psicologicos fuertes", "Pre-market high/low criticos"],
        "catalysts": ["Musk tweets/news", "Delivery numbers", "FSD news", "China data"],
        "avg_range": "4-10% daily range",
        "options_note": "IV cronicamente alta. Premium selling viable en rangos.",
    },
    "AMD": {
        "vwap_note": "Correlacion alta con NVDA. Suele seguir con rezago de 15-30min.",
        "key_levels": ["Ratio AMD/NVDA como senal de rotacion", "$100 soporte psicologico"],
        "catalysts": ["MI300X AI chip news", "Data center wins", "NVDA news"],
        "avg_range": "3-6% daily range",
        "options_note": "Buena liquidez en opciones. Spreads razonables.",
    },
}

DEFAULT_SCALP = {
    "vwap_note": "Seguir tendencia del mercado general (QQQ/SPY).",
    "key_levels": ["Pre-market high y low como niveles clave", "Redondos psicologicos"],
    "catalysts": ["Noticias sectoriales", "Datos macro del dia"],
    "avg_range": "2-4% daily range",
    "options_note": "Revisar IV rank vs historico antes de operar opciones.",
}

# ─── SIGNAL KEYWORDS ──────────────────────────────────────────

BULLISH_WORDS = {
    "beat", "beats", "exceeded", "surpassed", "strong", "growth", "raised guidance",
    "record", "profit", "outperform", "upgrade", "rally", "surge", "soar",
    "better than expected", "upside", "momentum", "acceleration", "wins",
    "optimistic", "robust", "solid", "expansion", "record high", "breakout",
    "positive", "recovery", "demand", "breakthrough", "jumped", "climbed",
}
BEARISH_WORDS = {
    "miss", "missed", "below", "decline", "weak", "cut guidance", "downgrade",
    "concern", "risk", "lower", "fall", "drop", "disappointing", "loss",
    "warning", "headwind", "slowdown", "uncertainty", "pressure", "layoff",
    "restructuring", "investigation", "lawsuit", "tariff", "recession",
    "contraction", "missed estimates", "worse than expected", "plunged", "tumbled",
}


# ─── FETCHING ─────────────────────────────────────────────────

def yf_get(ticker: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}?interval=1d&range=5d"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        result = data["chart"]["result"][0]
        meta   = result["meta"]
        closes = result["indicators"]["quote"][0].get("close", [])
        closes = [c for c in closes if c is not None]
        prev_close  = closes[-2] if len(closes) >= 2 else meta.get("previousClose", 0)
        price       = meta.get("regularMarketPrice") or meta.get("chartPreviousClose", 0)
        change_pct  = ((price - prev_close) / prev_close * 100) if prev_close else 0
        volume      = meta.get("regularMarketVolume", 0)
        day_high    = meta.get("regularMarketDayHigh", 0)
        day_low     = meta.get("regularMarketDayLow",  0)
        week52_high = meta.get("fiftyTwoWeekHigh", 0)
        week52_low  = meta.get("fiftyTwoWeekLow",  0)
        pre_price   = meta.get("preMarketPrice")
        pre_chg     = ((pre_price - price) / price * 100) if pre_price and price else None
        return {
            "price":       round(price, 2),
            "change_pct":  round(change_pct, 2),
            "prev_close":  round(prev_close, 2),
            "volume":      volume,
            "day_high":    round(day_high, 2),
            "day_low":     round(day_low,  2),
            "week52_high": round(week52_high, 2),
            "week52_low":  round(week52_low,  2),
            "pre_price":   round(pre_price, 2) if pre_price else None,
            "pre_chg":     round(pre_chg, 2)   if pre_chg  else None,
            "closes":      [round(c, 2) for c in closes[-5:]],
        }
    except Exception as e:
        print(f"  WARNING yfinance ({ticker}): {e}", file=sys.stderr)
        return {}


def cg_get_markets() -> list:
    ids = ",".join(c["id"] for c in CRYPTO_IDS)
    url = (f"https://api.coingecko.com/api/v3/coins/markets"
           f"?vs_currency=usd&ids={ids}&order=volume_desc"
           f"&per_page=50&page=1&sparkline=true&price_change_percentage=1h,24h,7d")
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  WARNING CoinGecko: {e}", file=sys.stderr)
        return []


def cg_global() -> dict:
    url = "https://api.coingecko.com/api/v3/global"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("data", {})
    except Exception as e:
        print(f"  WARNING CoinGecko global: {e}", file=sys.stderr)
        return {}


def fmp_get(endpoint: str, params: dict = {}) -> list:
    if not FMP_API_KEY:
        return []
    p = dict(params)
    p["apikey"] = FMP_API_KEY
    qs  = urllib.parse.urlencode(p)
    url = f"https://financialmodelingprep.com/stable/{endpoint}?{qs}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  WARNING FMP ({endpoint}): {e}", file=sys.stderr)
        return []


def fetch_futures() -> list:
    result = []
    for item in FUTURES:
        print(f"  {item['ticker']}...", end=" ")
        d = yf_get(item["ticker"])
        result.append({**item, "data": d})
        print("OK" if d else "FAIL")
        time.sleep(0.2)
    return result


def fetch_news() -> list:
    data = fmp_get("fmp-articles", {"limit": 50, "page": 0})
    if not isinstance(data, list) or len(data) == 0:
        return []
    out = []
    for item in data:
        raw_tickers = (item.get("tickers") or "").upper()
        symbols = {t.split(":")[-1].strip() for t in raw_tickers.split(",") if t.strip()}
        title   = (item.get("title") or "").lower()
        ticker_match  = bool(symbols & NEWS_TICKERS)
        keyword_match = any(k in title for k in NEWS_KEYWORDS)
        if ticker_match or keyword_match:
            display = ", ".join(sorted(symbols & NEWS_TICKERS)) if symbols & NEWS_TICKERS else "MACRO"
            content = item.get("content") or ""
            clean = re.sub(r"<[^>]+>", " ", content)
            clean = re.sub(r"\s+", " ", clean).strip()[:200]
            out.append({
                "title":     item.get("title", ""),
                "ticker":    display,
                "publisher": item.get("site", "FMP"),
                "date":      (item.get("date") or "")[:16],
                "url":       item.get("link", "#"),
                "text":      clean,
            })
        if len(out) >= 12:
            break
    return out


# ─── SIGNAL ENGINE ────────────────────────────────────────────

def news_sentiment(title: str, text: str) -> tuple:
    """Returns (score, label). Positive = bullish, negative = bearish."""
    combined = (title + " " + text).lower()
    bull = sum(1 for w in BULLISH_WORDS if w in combined)
    bear = sum(1 for w in BEARISH_WORDS if w in combined)
    score = bull - bear
    if score >= 2:   return score, "BULLISH"
    if score <= -2:  return score, "BEARISH"
    return score, "NEUTRAL"


def compute_risk(indices_data: list, futures_data: list) -> dict:
    vix = next((i["data"].get("price", 20) for i in indices_data
                if i["ticker"] == "^VIX" and i["data"]), 20)
    vix_chg = next((i["data"].get("change_pct", 0) for i in indices_data
                    if i["ticker"] == "^VIX" and i["data"]), 0)
    nq_chg  = next((f["data"].get("change_pct", 0) for f in futures_data
                    if f["ticker"] == "NQ=F" and f["data"]), 0)

    if vix < 15:
        level, color = "BAJO", "#00d4aa"
    elif vix < 20:
        level, color = "MODERADO", "#ffa502"
    elif vix < 28:
        level, color = "ELEVADO", "#ff6b35"
    else:
        level, color = "EXTREMO", "#ff4757"

    # Large futures move upgrades risk
    if abs(nq_chg) > 2.5 and level == "BAJO":
        level, color = "MODERADO", "#ffa502"

    vix_trend = "cayendo" if vix_chg < -3 else ("subiendo" if vix_chg > 3 else "estable")
    return {"level": level, "color": color, "vix": vix, "vix_chg": vix_chg,
            "vix_trend": vix_trend, "nq_chg": nq_chg}


def compute_market_signal(indices_data: list, futures_data: list, news: list) -> dict:
    score = 0
    factors = []  # (icon, text)

    # VIX
    vix_data = next((i["data"] for i in indices_data
                     if i["ticker"] == "^VIX" and i["data"]), {})
    vix     = vix_data.get("price", 20) or 20
    vix_chg = vix_data.get("change_pct", 0) or 0
    if vix < 15:
        score += 2
        factors.append(("pos", f"VIX {vix:.1f} ({vix_chg:+.1f}%) — volatilidad baja, sesgo risk-on"))
    elif vix < 20:
        score += 1
        factors.append(("pos", f"VIX {vix:.1f} ({vix_chg:+.1f}%) — volatilidad controlada"))
    elif vix < 25:
        score -= 1
        factors.append(("neg", f"VIX {vix:.1f} ({vix_chg:+.1f}%) — volatilidad elevada, precaución"))
    else:
        score -= 2
        factors.append(("neg", f"VIX {vix:.1f} ({vix_chg:+.1f}%) — miedo en el mercado"))

    # Futures NQ + ES
    nq_chg = next((f["data"].get("change_pct", 0) for f in futures_data
                   if f["ticker"] == "NQ=F" and f["data"]), 0) or 0
    es_chg = next((f["data"].get("change_pct", 0) for f in futures_data
                   if f["ticker"] == "ES=F" and f["data"]), 0) or 0
    avg_fut = (nq_chg + es_chg) / 2
    if avg_fut > 1:
        score += 2
        factors.append(("pos", f"Futuros alcistas — NQ {nq_chg:+.2f}% · ES {es_chg:+.2f}%"))
    elif avg_fut > 0.3:
        score += 1
        factors.append(("pos", f"Futuros positivos — NQ {nq_chg:+.2f}% · ES {es_chg:+.2f}%"))
    elif avg_fut < -1:
        score -= 2
        factors.append(("neg", f"Futuros bajistas — NQ {nq_chg:+.2f}% · ES {es_chg:+.2f}%"))
    elif avg_fut < -0.3:
        score -= 1
        factors.append(("neg", f"Futuros negativos — NQ {nq_chg:+.2f}% · ES {es_chg:+.2f}%"))
    else:
        factors.append(("neu", f"Futuros planos — NQ {nq_chg:+.2f}% · ES {es_chg:+.2f}%"))

    # Market breadth (excl. VIX)
    chgs = [i["data"].get("change_pct", 0) for i in indices_data
            if i["data"] and i["ticker"] != "^VIX"]
    if chgs:
        n_pos = sum(1 for c in chgs if c > 0)
        breadth = n_pos / len(chgs)
        if breadth >= 0.8:
            score += 1
            factors.append(("pos", f"Amplitud positiva — {n_pos}/{len(chgs)} índices al alza"))
        elif breadth <= 0.2:
            score -= 1
            factors.append(("neg", f"Amplitud negativa — {n_pos}/{len(chgs)} índices al alza"))
        else:
            factors.append(("neu", f"Amplitud mixta — {n_pos}/{len(chgs)} índices al alza"))

    # News sentiment
    if news:
        sent_scores = [news_sentiment(n["title"], n.get("text",""))[0] for n in news]
        avg_sent = sum(sent_scores) / len(sent_scores)
        bull_count = sum(1 for s in sent_scores if s > 0)
        bear_count = sum(1 for s in sent_scores if s < 0)
        if avg_sent > 0.5:
            score += 1
            factors.append(("pos", f"Noticias alcistas — {bull_count} positivas / {bear_count} negativas"))
        elif avg_sent < -0.5:
            score -= 1
            factors.append(("neg", f"Noticias bajistas — {bull_count} positivas / {bear_count} negativas"))
        else:
            factors.append(("neu", f"Noticias mixtas — {bull_count} positivas / {bear_count} negativas"))

    # Signal label
    if score >= 5:
        label, color, emoji = "COMPRA FUERTE", "#00d4aa", "▲▲"
    elif score >= 3:
        label, color, emoji = "COMPRA", "#00d4aa", "▲"
    elif score >= 1:
        label, color, emoji = "SESGO ALCISTA", "#3b82f6", "↗"
    elif score > -1:
        label, color, emoji = "NEUTRAL", "#6b7280", "→"
    elif score > -3:
        label, color, emoji = "SESGO BAJISTA", "#ffa502", "↘"
    elif score > -5:
        label, color, emoji = "VENTA", "#ff4757", "▼"
    else:
        label, color, emoji = "VENTA FUERTE", "#ff4757", "▼▼"

    return {"label": label, "color": color, "emoji": emoji,
            "score": score, "factors": factors}


def get_setup_tip(signal_label: str, risk_level: str) -> str:
    tips = {
        ("COMPRA FUERTE",  "BAJO"):      "Agresivo: longs en cualquier pullback, size máximo. Trailing stop amplio.",
        ("COMPRA FUERTE",  "MODERADO"):  "Fuerte sesgo largo. Size alto. Longs en pullbacks a VWAP, confirmar con volumen.",
        ("COMPRA",         "BAJO"):      "Sesgo largo claro. Size normal-alto. Comprar breaks de pre-market high.",
        ("COMPRA",         "MODERADO"):  "Sesgo largo. Size estándar. Entradas en pullbacks a VWAP con confirmación.",
        ("COMPRA",         "ELEVADO"):   "Sesgo largo con precaución. Reducir size 30%. Esperar confirmación en VWAP.",
        ("SESGO ALCISTA",  "BAJO"):      "Ligero sesgo largo. Size reducido. Confirmar dirección con los primeros 15min.",
        ("SESGO ALCISTA",  "MODERADO"):  "Ligero sesgo largo. Size reducido. Esperar setup claro, no perseguir.",
        ("SESGO ALCISTA",  "ELEVADO"):   "Mercado mixto con riesgo elevado. Size mínimo, solo setups A+.",
        ("NEUTRAL",        "BAJO"):      "Mercado lateral. Range trading: comprar soporte, vender resistencia.",
        ("NEUTRAL",        "MODERADO"):  "Sin sesgo claro. Esperar ruptura de rango o no operar.",
        ("NEUTRAL",        "ELEVADO"):   "Riesgo elevado sin dirección. Mejor no operar.",
        ("NEUTRAL",        "EXTREMO"):   "VIX extremo. NO OPERAR hasta que el mercado muestre dirección.",
        ("SESGO BAJISTA",  "MODERADO"):  "Ligero sesgo corto. Size reducido. Shorts en rebotes fallidos a VWAP.",
        ("SESGO BAJISTA",  "ELEVADO"):   "Sesgo bajista con riesgo alto. Shorts selectivos en rebotes, stop ajustado.",
        ("VENTA",          "ELEVADO"):   "Sesgo corto. Shorts en rebotes a VWAP. Evitar longs hasta recaptura de nivel clave.",
        ("VENTA",          "EXTREMO"):   "Mercado en distribución. Size mínimo. Solo shorts muy selectivos.",
        ("VENTA FUERTE",   "ELEVADO"):   "Mercado bajista. Solo shorts, no longs. Gestión de riesgo estricta.",
        ("VENTA FUERTE",   "EXTREMO"):   "Pánico en el mercado. NO OPERAR. Si operas, micro-size en shorts y salida rápida.",
    }
    key = (signal_label, risk_level)
    if key in tips:
        return tips[key]
    if "COMPRA" in signal_label:
        return f"Sesgo alcista. Adaptar size al riesgo actual ({risk_level})."
    if "VENTA" in signal_label:
        return f"Sesgo bajista. Adaptar size al riesgo actual ({risk_level})."
    return "Mercado sin sesgo claro. Esperar setup definido antes de operar."


def compute_stock_signal(stock: dict, news: list, market_score: int = 0) -> dict:
    d = stock["data"]
    if not d:
        return {"label": "S/D", "color": "#6b7280", "bg": "transparent",
                "score": 0, "reason": "Sin datos"}

    score = 0
    reasons = []
    ticker = stock["ticker"]

    # Day change momentum
    chg = d.get("change_pct", 0) or 0
    if chg > 4:
        score += 3; reasons.append(f"Gap fuerte +{chg:.1f}%")
    elif chg > 2:
        score += 2; reasons.append(f"Momentum alcista +{chg:.1f}%")
    elif chg > 0.5:
        score += 1; reasons.append(f"Tendencia positiva +{chg:.1f}%")
    elif chg < -4:
        score -= 3; reasons.append(f"Caida fuerte {chg:.1f}%")
    elif chg < -2:
        score -= 2; reasons.append(f"Presion bajista {chg:.1f}%")
    elif chg < -0.5:
        score -= 1; reasons.append(f"Debilidad relativa {chg:.1f}%")

    # 5-day trend
    closes = d.get("closes", [])
    if len(closes) >= 3 and closes[0]:
        trend = (closes[-1] - closes[0]) / closes[0] * 100
        if trend > 5:
            score += 2; reasons.append("Tendencia 5d fuerte")
        elif trend > 2:
            score += 1
        elif trend < -5:
            score -= 2; reasons.append("Tendencia 5d bajista")
        elif trend < -2:
            score -= 1

    # Pre-market
    pre = d.get("pre_chg")
    if pre is not None:
        if pre > 2:
            score += 2; reasons.append(f"Pre-mkt fuerte +{pre:.1f}%")
        elif pre > 0.5:
            score += 1; reasons.append(f"Pre-mkt positivo")
        elif pre < -2:
            score -= 2; reasons.append(f"Pre-mkt debil {pre:.1f}%")
        elif pre < -0.5:
            score -= 1

    # News catalyst for this specific ticker
    for n in news:
        if ticker in (n.get("ticker") or ""):
            sent_score, sent_label = news_sentiment(n["title"], n.get("text", ""))
            if sent_score >= 2:
                score += 2; reasons.append(f"Noticia positiva ({sent_label})")
            elif sent_score >= 1:
                score += 1; reasons.append("Catalizador positivo en noticias")
            elif sent_score <= -2:
                score -= 2; reasons.append(f"Noticia negativa ({sent_label})")
            elif sent_score <= -1:
                score -= 1; reasons.append("Catalizador negativo en noticias")
            break

    # 52-week position
    w52h  = d.get("week52_high") or 0
    w52l  = d.get("week52_low")  or 0
    price = d.get("price")       or 0
    if w52h and w52l and w52h != w52l:
        pos = (price - w52l) / (w52h - w52l) * 100
        if pos > 95 and chg > 0:
            score -= 1; reasons.append("Cerca de maximo anual (resistencia)")
        elif pos < 10:
            score += 1; reasons.append("Cerca de minimo anual (soporte potencial)")

    # Market context slight weight
    if market_score >= 3:
        score += 1
    elif market_score <= -3:
        score -= 1

    reason_str = reasons[0] if reasons else "Momentum neutro"

    if score >= 5:
        return {"label": "STRONG BUY", "color": "#00d4aa", "bg": "rgba(0,212,170,0.12)",
                "score": score, "reason": reason_str}
    elif score >= 3:
        return {"label": "BUY",        "color": "#00d4aa", "bg": "rgba(0,212,170,0.08)",
                "score": score, "reason": reason_str}
    elif score >= 1:
        return {"label": "LONG BIAS",  "color": "#3b82f6", "bg": "rgba(59,130,246,0.08)",
                "score": score, "reason": reason_str}
    elif score > -1:
        return {"label": "NEUTRAL",    "color": "#6b7280", "bg": "rgba(107,114,128,0.06)",
                "score": score, "reason": reason_str}
    elif score > -3:
        return {"label": "SHORT BIAS", "color": "#ffa502", "bg": "rgba(255,165,2,0.08)",
                "score": score, "reason": reason_str}
    elif score > -5:
        return {"label": "SELL",       "color": "#ff4757", "bg": "rgba(255,71,87,0.08)",
                "score": score, "reason": reason_str}
    else:
        return {"label": "STRONG SELL","color": "#ff4757", "bg": "rgba(255,71,87,0.12)",
                "score": score, "reason": reason_str}


# ─── HTML HELPERS ─────────────────────────────────────────────

def fmt_vol(n):
    if not n: return "-"
    if n >= 1e9: return f"{n/1e9:.1f}B"
    if n >= 1e6: return f"{n/1e6:.1f}M"
    if n >= 1e3: return f"{n/1e3:.0f}K"
    return str(n)


def chg_class(v):
    if v is None: return "neutral"
    return "up" if v > 0 else ("down" if v < 0 else "neutral")


def chg_str(v, decimals=2):
    if v is None: return "-"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.{decimals}f}%"


def sparkline_svg(closes: list, width=80, height=28) -> str:
    if len(closes) < 2:
        return ""
    mn, mx = min(closes), max(closes)
    rng = mx - mn or 1
    pts = []
    for i, c in enumerate(closes):
        x = i / (len(closes) - 1) * width
        y = height - (c - mn) / rng * height
        pts.append(f"{x:.1f},{y:.1f}")
    color = "#00d4aa" if closes[-1] >= closes[0] else "#ff4757"
    return (f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" '
            f'stroke-width="1.5" stroke-linejoin="round"/></svg>')


def mini_bar(pct, max_pct=5.0) -> str:
    capped = max(min(abs(pct or 0), max_pct), 0)
    w = capped / max_pct * 100
    color = "#00d4aa" if (pct or 0) >= 0 else "#ff4757"
    return (f'<div style="height:3px;border-radius:2px;background:rgba(255,255,255,0.05);margin-top:4px">'
            f'<div style="height:3px;border-radius:2px;width:{w:.0f}%;background:{color}"></div></div>')


def range_bar(price, low, high) -> str:
    if not all([price, low, high]) or high == low:
        return ""
    pct = max(0, min(100, (price - low) / (high - low) * 100))
    return (f'<div style="position:relative;height:4px;background:rgba(255,255,255,0.08);border-radius:2px;margin:4px 0">'
            f'<div style="position:absolute;top:-2px;left:{pct:.0f}%;width:8px;height:8px;'
            f'border-radius:50%;background:#ffa502;transform:translateX(-50%)"></div></div>'
            f'<div style="display:flex;justify-content:space-between;font-size:10px;color:#6b7280">'
            f'<span>${low:,.2f}</span><span>${high:,.2f}</span></div>')


# ─── HTML SECTION BUILDERS ────────────────────────────────────

def build_market_signal_html(market_signal: dict, risk: dict) -> str:
    setup = get_setup_tip(market_signal["label"], risk["level"])

    factor_rows = ""
    icon_map = {"pos": ("✓", "#00d4aa"), "neg": ("✗", "#ff4757"), "neu": ("≈", "#6b7280")}
    for kind, text in market_signal["factors"]:
        sym, col = icon_map.get(kind, ("·", "#6b7280"))
        factor_rows += f'<div class="sig-factor"><span style="color:{col};font-weight:700;min-width:14px">{sym}</span><span>{text}</span></div>'

    score_sign = "+" if market_signal["score"] >= 0 else ""
    vix_col = risk["color"]

    return f"""
<div class="signal-card">
  <div class="signal-top">
    <div class="signal-main-block">
      <div class="signal-emoji">{market_signal["emoji"]}</div>
      <div>
        <div class="signal-label-big" style="color:{market_signal['color']}">{market_signal['label']}</div>
        <div class="signal-score-text">Puntuacion: <span style="color:{market_signal['color']};font-weight:700">{score_sign}{market_signal['score']}</span></div>
      </div>
    </div>
    <div class="risk-block">
      <div class="risk-label" style="color:{vix_col}">RIESGO {risk['level']}</div>
      <div class="risk-vix">VIX <span style="color:{vix_col};font-weight:700">{risk['vix']:.1f}</span> <span style="font-size:10px;color:#6b7280">({risk['vix_chg']:+.1f}% — {risk['vix_trend']})</span></div>
    </div>
  </div>
  <div class="signal-factors-grid">{factor_rows}</div>
  <div class="signal-setup">
    <span style="color:#ffa502;font-weight:600;margin-right:6px">Setup:</span>{setup}
  </div>
</div>"""


def build_indices_html(indices_data: list) -> str:
    cards = []
    for item in indices_data:
        d = item["data"]
        if not d:
            continue
        chg  = d.get("change_pct", 0)
        cc   = chg_class(chg)
        pre  = d.get("pre_chg")
        pre_html = ""
        if pre is not None:
            pre_html = f'<span class="pre-badge {chg_class(pre)}">PRE {chg_str(pre)}</span>'
        spark = sparkline_svg(d.get("closes", []))
        cards.append(f"""
        <div class="index-card {cc}-border">
          <div class="index-top">
            <div>
              <div class="index-name">{item['short']}</div>
              <div class="index-fullname">{item['name']}</div>
            </div>
            <div class="index-right">{spark}{pre_html}</div>
          </div>
          <div class="index-price">{d['price']:,.2f}</div>
          <div class="index-chg {cc}">{chg_str(chg)}</div>
          {mini_bar(chg)}
        </div>""")
    return "\n".join(cards)


def build_futures_html(futures_data: list) -> str:
    if not futures_data:
        return ""
    cards = []
    for item in futures_data:
        d = item["data"]
        if not d:
            continue
        chg   = d.get("change_pct", 0)
        cc    = chg_class(chg)
        price = d.get("price", 0)
        pre   = d.get("pre_chg")
        pre_html = ""
        if pre is not None:
            pre_html = f'<span class="pre-badge {chg_class(pre)}">PRE {chg_str(pre)}</span>'
        spark      = sparkline_svg(d.get("closes", []))
        top_border = "#00d4aa" if chg >= 0 else "#ff4757"
        cards.append(f"""
        <div class="index-card {cc}-border" style="border-top:2px solid {top_border}">
          <div class="index-top">
            <div>
              <div class="index-name">{item['short']}</div>
              <div class="index-fullname">{item['name']}</div>
            </div>
            <div class="index-right">{spark}{pre_html}</div>
          </div>
          <div class="index-price">{price:,.2f}</div>
          <div class="index-chg {cc}">{chg_str(chg)}</div>
          {mini_bar(chg)}
        </div>""")
    return "\n".join(cards)


def build_news_html(news: list) -> str:
    if not news:
        return '<p style="color:#6b7280;font-size:12px;font-family:monospace;padding:1rem 0">No news available — check FMP_API_KEY.</p>'
    ticker_colors = {
        "NVDA":"#00d4aa","AMD":"#00d4aa","MSFT":"#3b82f6","AAPL":"#3b82f6",
        "GOOGL":"#3b82f6","META":"#ffa502","AMZN":"#ffa502","TSLA":"#ff4757",
        "SPY":"#6b7280","QQQ":"#6b7280","MACRO":"#6b7280",
    }
    sent_cfg = {
        "BULLISH": ("▲", "#00d4aa", "rgba(0,212,170,0.1)"),
        "BEARISH": ("▼", "#ff4757", "rgba(255,71,87,0.1)"),
        "NEUTRAL": ("—", "#6b7280", "rgba(107,114,128,0.08)"),
    }
    rows = []
    for n in news:
        t   = n["ticker"].split(",")[0].strip()
        col = ticker_colors.get(t, "#6b7280")
        ticker_badge = (f'<span style="font-size:10px;padding:1px 7px;border-radius:4px;'
                        f'background:{col}22;color:{col};font-family:monospace;font-weight:600">{t}</span>')

        _, sent_label = news_sentiment(n["title"], n.get("text", ""))
        sym, scol, sbg = sent_cfg[sent_label]
        sent_badge = (f'<span style="font-size:10px;padding:1px 6px;border-radius:4px;'
                      f'background:{sbg};color:{scol};font-family:monospace;font-weight:700">'
                      f'{sym} {sent_label}</span>')

        url = n.get("url", "#")
        rows.append(f"""
        <div class="news-row">
          <div class="news-meta">{ticker_badge}{sent_badge}<span class="news-pub">{n['publisher']}</span><span class="news-date">{n['date']}</span></div>
          <a class="news-title" href="{url}" target="_blank">{n['title']}</a>
          <p class="news-text">{n['text']}</p>
        </div>""")
    return "\n".join(rows)


def build_stocks_html(stocks_data: list, news: list, market_score: int = 0) -> str:
    rows = []
    for item in stocks_data:
        d    = item["data"]
        meta = SCALP_META.get(item["ticker"], DEFAULT_SCALP)
        sig  = compute_stock_signal(item, news, market_score)

        if not d:
            rows.append(f'<tr><td>{item["ticker"]}</td><td colspan="9" style="color:#6b7280">No data</td></tr>')
            continue

        chg   = d.get("change_pct", 0)
        cc    = chg_class(chg)
        pre   = d.get("pre_chg")
        pre_html = f'<span class="{chg_class(pre)}" style="font-size:10px;font-family:monospace">{chg_str(pre)}</span>' if pre is not None else '<span style="color:#6b7280;font-size:10px">-</span>'
        spark = sparkline_svg(d.get("closes", []), 60, 22)
        price = d.get("price", 0)
        w52h  = d.get("week52_high", 0)
        w52l  = d.get("week52_low",  0)
        w52_pct = ((price - w52l) / (w52h - w52l) * 100) if w52h and w52l and w52h != w52l else 0
        w52_bar = (f'<div style="width:50px;height:3px;background:rgba(255,255,255,0.08);border-radius:2px;display:inline-block;vertical-align:middle">'
                   f'<div style="width:{w52_pct:.0f}%;height:3px;background:#ffa502;border-radius:2px"></div></div>')

        sig_badge = (f'<div class="sig-badge" style="color:{sig["color"]};background:{sig["bg"]};border-color:{sig["color"]}40">'
                     f'{sig["label"]}</div>'
                     f'<div style="font-size:9px;color:#6b7280;margin-top:2px;max-width:80px;line-height:1.3">{sig["reason"]}</div>')

        watch_li = "".join(f"<li>{w}</li>" for w in meta["key_levels"])
        cat_li   = "".join(f"<li>{c}</li>" for c in meta["catalysts"])
        expanded = f"""
        <tr class="stock-expanded" id="exp-{item['ticker']}" style="display:none">
          <td colspan="10" style="padding:0 12px 12px 48px">
            <div class="expanded-grid">
              <div>
                <div class="exp-title">Niveles clave</div>
                <ul class="exp-list">{watch_li}</ul>
                <div class="exp-title" style="margin-top:8px">VWAP / Setup</div>
                <p class="exp-note">{meta['vwap_note']}</p>
              </div>
              <div>
                <div class="exp-title">Catalizadores</div>
                <ul class="exp-list">{cat_li}</ul>
                <div class="exp-title" style="margin-top:8px">Range / Opciones</div>
                <p class="exp-note">{meta['avg_range']}</p>
                <p class="exp-note">{meta['options_note']}</p>
              </div>
            </div>
          </td>
        </tr>"""
        rows.append(f"""
        <tr class="stock-row" onclick="toggleRow('{item['ticker']}')" data-ticker="{item['ticker']}">
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <img class="stock-logo" src="https://logo.clearbit.com/{item['ticker'].lower()}.com" onerror="this.style.display='none'" alt="">
              <div>
                <div style="font-weight:600;font-size:13px;font-family:monospace">{item['ticker']}</div>
                <div style="font-size:11px;color:#6b7280">{item['name']}</div>
              </div>
            </div>
          </td>
          <td><span class="sector-pill">{item['sector']}</span></td>
          <td class="price-cell" style="font-family:monospace">${price:,.2f}</td>
          <td class="{cc}" style="font-family:monospace">{chg_str(chg)}</td>
          <td>{pre_html}</td>
          <td style="color:#6b7280;font-size:11px;font-family:monospace">{fmt_vol(d.get('volume'))}</td>
          <td>{range_bar(price, d.get('day_low', 0), d.get('day_high', 0))}</td>
          <td>{w52_bar}</td>
          <td>{spark}</td>
          <td>{sig_badge}</td>
        </tr>
        {expanded}""")
    return "\n".join(rows)


def build_crypto_html(crypto_data: list, global_data: dict) -> str:
    total_mcap = global_data.get("total_market_cap", {}).get("usd") or 0
    btc_dom    = global_data.get("market_cap_percentage", {}).get("btc") or 0
    eth_dom    = global_data.get("market_cap_percentage", {}).get("eth") or 0
    total_vol  = global_data.get("total_volume", {}).get("usd") or 0
    mcap_g = f"${total_mcap/1e12:.2f}T" if total_mcap else "-"
    vol_g  = f"${total_vol/1e9:.0f}B"   if total_vol  else "-"
    global_bar = f"""
    <div class="crypto-global">
      <div class="cg-item"><span class="cg-label">Total MCap</span><span class="cg-val">{mcap_g}</span></div>
      <div class="cg-item"><span class="cg-label">BTC Dom</span><span class="cg-val amber">{btc_dom:.1f}%</span></div>
      <div class="cg-item"><span class="cg-label">ETH Dom</span><span class="cg-val">{eth_dom:.1f}%</span></div>
      <div class="cg-item"><span class="cg-label">24h Vol</span><span class="cg-val">{vol_g}</span></div>
    </div>"""
    by_id = {c["id"]: c for c in crypto_data}
    cards = []
    for item in CRYPTO_IDS:
        d = by_id.get(item["id"])
        if not d:
            continue
        price   = d.get("current_price") or 0
        chg_1h  = d.get("price_change_percentage_1h_in_currency") or 0
        chg_24h = d.get("price_change_percentage_24h_in_currency") or 0
        chg_7d  = d.get("price_change_percentage_7d_in_currency") or 0
        volume  = d.get("total_volume") or 0
        mcap    = d.get("market_cap") or 0
        ath_pct = d.get("ath_change_percentage") or 0
        spark_prices = d.get("sparkline_in_7d", {}).get("price", [])
        if len(spark_prices) > 20:
            step = len(spark_prices) // 20
            spark_prices = spark_prices[::step][:20]
        spark = sparkline_svg([round(p, 4) for p in spark_prices if p], 80, 28)
        if not price:
            price_str = "-"
        elif price >= 1000:
            price_str = f"${price:,.0f}"
        elif price >= 1:
            price_str = f"${price:,.2f}"
        else:
            price_str = f"${price:.6f}"
        vol_str  = f"${volume/1e6:.0f}M" if volume else "-"
        mcap_str = f"${mcap/1e9:.1f}B"   if mcap   else "-"
        ath_str  = f"{ath_pct:.0f}%"      if ath_pct else "-"
        logo_url = d.get("image", "")
        cards.append(f"""
        <div class="crypto-card">
          <div class="crypto-header">
            <img class="crypto-logo" src="{logo_url}" alt="{item['ticker']}">
            <div>
              <div class="crypto-ticker">{item['ticker']}</div>
              <div class="crypto-name">{item['name']}</div>
            </div>
            <div style="margin-left:auto">{spark}</div>
          </div>
          <div class="crypto-price">{price_str}</div>
          <div class="crypto-changes">
            <div class="chg-item"><div class="chg-label">1h</div><div class="chg-val {chg_class(chg_1h)}">{chg_str(chg_1h)}</div></div>
            <div class="chg-item"><div class="chg-label">24h</div><div class="chg-val {chg_class(chg_24h)}">{chg_str(chg_24h)}</div></div>
            <div class="chg-item"><div class="chg-label">7d</div><div class="chg-val {chg_class(chg_7d)}">{chg_str(chg_7d)}</div></div>
          </div>
          <div class="crypto-footer">
            <span class="cg-label">Vol 24h</span> <span style="font-size:11px;font-family:monospace">{vol_str}</span>
            &nbsp;·&nbsp;
            <span class="cg-label">MCap</span> <span style="font-size:11px;font-family:monospace">{mcap_str}</span>
            &nbsp;·&nbsp;
            <span class="cg-label">vs ATH</span> <span class="{chg_class(ath_pct)}" style="font-size:11px;font-family:monospace">{ath_str}</span>
          </div>
          {mini_bar(chg_24h, 10)}
        </div>""")
    return global_bar + '\n<div class="crypto-grid">\n' + "\n".join(cards) + "\n</div>"


def build_macro_html() -> str:
    week_events = [
        {"day": "Lunes",     "event": "PMI Manufacturing Flash",     "impact": "medium"},
        {"day": "Martes",    "event": "Consumer Confidence (CB)",    "impact": "high"},
        {"day": "Miercoles", "event": "ADP Employment / Fed Minutes","impact": "high"},
        {"day": "Jueves",    "event": "Jobless Claims / GDP",        "impact": "high"},
        {"day": "Viernes",   "event": "NFP / CPI / PCE",             "impact": "critical"},
    ]
    rows = ""
    for e in week_events:
        ic = {"critical": "red", "high": "amber", "medium": "neutral"}.get(e["impact"], "neutral")
        rows += f"""
        <div class="macro-row">
          <span class="macro-day">{e['day']}</span>
          <span class="macro-event">{e['event']}</span>
          <span class="impact-badge {ic}">{e['impact']}</span>
        </div>"""
    tips = [
        "VIX > 20: reducir size, spreads mas anchos",
        "VIX > 30: solo scalps muy cortos o no operar",
        "Evitar posiciones 30min antes y despues de datos macro",
        "FOMC days: esperar la primera reaccion antes de entrar",
        "Earnings day: no operar el subyacente los primeros 5min",
        "Pre-market gap > 3%: esperar VWAP retest antes de seguir tendencia",
        "NQ y SPX divergen: senal de indecision, reducir exposicion",
    ]
    tips_html = "".join(f"<li>{t}</li>" for t in tips)
    return f"""
    <div class="macro-grid">
      <div class="macro-calendar">
        <div class="section-sub">Calendario macro semanal</div>
        {rows}
      </div>
      <div class="macro-rules">
        <div class="section-sub">Reglas de gestion de riesgo</div>
        <ul class="rules-list">{tips_html}</ul>
      </div>
    </div>"""


# ─── MAIN HTML ────────────────────────────────────────────────

def build_html(indices_data, stocks_data, crypto_html, macro_html,
               futures_data=None, news=None,
               market_signal=None, risk=None) -> str:
    now          = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    today        = datetime.date.today()
    indices_html = build_indices_html(indices_data)
    futures_html = build_futures_html(futures_data or [])
    news_html    = build_news_html(news or [])
    market_score = (market_signal or {}).get("score", 0)
    stocks_html  = build_stocks_html(stocks_data, news or [], market_score)
    sig_html     = build_market_signal_html(market_signal, risk) if market_signal and risk else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Day Trading Dashboard - {today.strftime('%b %d, %Y')}</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#08090d;--surface:#0f1117;--surface2:#161820;--surface3:#1c1e28;
  --border:rgba(255,255,255,0.06);--border2:rgba(255,255,255,0.12);
  --text:#e8eaf0;--muted:#6b7280;
  --green:#00d4aa;--red:#ff4757;--amber:#ffa502;--blue:#3b82f6;
}}
body{{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;min-height:100vh}}
.up{{color:var(--green)}}.down{{color:var(--red)}}.neutral{{color:var(--muted)}}.amber{{color:var(--amber)}}
.header{{background:var(--surface);border-bottom:1px solid var(--border);padding:1rem 1.5rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}}
.header h1{{font-size:1.1rem;font-weight:600}}
.header p{{font-size:0.72rem;color:var(--muted);font-family:'JetBrains Mono',monospace}}
.live-dot{{width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;margin-right:6px;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
.tabs{{display:flex;gap:2px;background:var(--surface);border-bottom:1px solid var(--border);padding:0 1.5rem}}
.tab-btn{{font-size:0.8rem;padding:10px 16px;background:transparent;border:none;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;transition:all 0.15s}}
.tab-btn:hover{{color:var(--text)}}
.tab-btn.active{{color:var(--green);border-bottom-color:var(--green);font-weight:500}}
.tab-content{{display:none;padding:1.5rem;max-width:1400px;margin:0 auto}}
.tab-content.active{{display:block}}
.section-title{{font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-bottom:1rem;padding-bottom:0.5rem;border-bottom:1px solid var(--border)}}
.section-sub{{font-size:0.68rem;text-transform:uppercase;letter-spacing:0.08em;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-bottom:0.75rem;font-weight:600}}
.indices-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin-bottom:2rem}}
.index-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px}}
.up-border{{border-color:rgba(0,212,170,0.2)}}.down-border{{border-color:rgba(255,71,87,0.2)}}
.index-top{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px}}
.index-name{{font-family:'JetBrains Mono',monospace;font-size:0.8rem;font-weight:600}}
.index-fullname{{font-size:0.65rem;color:var(--muted);margin-top:2px}}
.index-right{{text-align:right}}
.index-price{{font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:600;margin-bottom:2px}}
.index-chg{{font-family:'JetBrains Mono',monospace;font-size:0.78rem;font-weight:500}}
.pre-badge{{font-family:'JetBrains Mono',monospace;font-size:0.62rem;padding:1px 5px;border-radius:3px;background:rgba(255,255,255,0.06);margin-top:3px;display:inline-block}}
/* ── MARKET SIGNAL CARD ── */
.signal-card{{background:var(--surface);border:1px solid var(--border2);border-radius:12px;padding:1rem 1.2rem;margin-bottom:1.5rem}}
.signal-top{{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;margin-bottom:0.75rem}}
.signal-main-block{{display:flex;align-items:center;gap:12px}}
.signal-emoji{{font-size:1.6rem;line-height:1}}
.signal-label-big{{font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:700;letter-spacing:0.05em}}
.signal-score-text{{font-size:0.72rem;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-top:3px}}
.risk-block{{text-align:right}}
.risk-label{{font-family:'JetBrains Mono',monospace;font-size:0.75rem;font-weight:700;letter-spacing:0.06em}}
.risk-vix{{font-size:0.72rem;font-family:'JetBrains Mono',monospace;color:var(--muted);margin-top:3px}}
.signal-factors-grid{{display:flex;flex-direction:column;gap:4px;margin-bottom:0.75rem}}
.sig-factor{{display:flex;align-items:flex-start;gap:8px;font-size:0.76rem;color:var(--muted);font-family:'JetBrains Mono',monospace;line-height:1.4}}
.signal-setup{{font-size:0.78rem;color:var(--muted);background:var(--surface2);border-radius:6px;padding:8px 12px;border-left:3px solid var(--amber);line-height:1.5}}
/* ── SIGNAL BADGE (stocks) ── */
.sig-badge{{font-family:'JetBrains Mono',monospace;font-size:0.65rem;font-weight:700;padding:2px 7px;border-radius:4px;border:1px solid;white-space:nowrap;display:inline-block;letter-spacing:0.04em}}
/* ── NEWS ── */
.news-list{{display:flex;flex-direction:column}}
.news-row{{padding:10px 0;border-bottom:1px solid var(--border)}}
.news-row:last-child{{border-bottom:none}}
.news-meta{{display:flex;align-items:center;gap:6px;margin-bottom:4px;flex-wrap:wrap}}
.news-pub{{font-size:11px;color:var(--muted);font-family:'JetBrains Mono',monospace}}
.news-date{{font-size:11px;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-left:auto}}
.news-title{{font-size:13px;font-weight:500;color:var(--text);text-decoration:none;display:block;margin-bottom:3px;line-height:1.4}}
.news-title:hover{{color:var(--green)}}
.news-text{{font-size:11px;color:var(--muted);line-height:1.5}}
/* ── STOCKS TABLE ── */
.table-wrap{{overflow-x:auto;border-radius:10px;border:1px solid var(--border)}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
thead th{{background:var(--surface2);padding:8px 12px;text-align:left;font-size:0.65rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);font-family:'JetBrains Mono',monospace;white-space:nowrap;border-bottom:1px solid var(--border)}}
.stock-row{{background:var(--surface);cursor:pointer;transition:background 0.15s;border-bottom:1px solid var(--border)}}
.stock-row:hover{{background:var(--surface2)}}
.stock-expanded td{{background:var(--surface3);border-bottom:1px solid var(--border)}}
td{{padding:10px 12px;vertical-align:middle}}
.stock-logo{{width:24px;height:24px;border-radius:6px;object-fit:contain;background:var(--surface2)}}
.price-cell{{font-weight:600;font-size:14px}}
.sector-pill{{font-size:10px;padding:2px 7px;border-radius:4px;background:rgba(255,165,2,0.12);color:var(--amber);font-family:'JetBrains Mono',monospace;white-space:nowrap}}
.expanded-grid{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}}
.exp-title{{font-size:0.65rem;text-transform:uppercase;letter-spacing:0.07em;color:var(--green);font-family:'JetBrains Mono',monospace;margin-bottom:6px;font-weight:600}}
.exp-list{{list-style:none;display:flex;flex-direction:column;gap:4px}}
.exp-list li{{font-size:0.76rem;color:var(--muted);padding-left:12px;position:relative;line-height:1.4}}
.exp-list li::before{{content:'>';position:absolute;left:0;color:var(--green)}}
.exp-note{{font-size:0.76rem;color:var(--muted);line-height:1.5;margin-top:4px}}
/* ── CRYPTO ── */
.crypto-global{{display:flex;gap:1.5rem;flex-wrap:wrap;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 16px;margin-bottom:1.5rem}}
.cg-item{{display:flex;flex-direction:column;gap:2px}}
.cg-label{{font-size:0.62rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);font-family:'JetBrains Mono',monospace}}
.cg-val{{font-family:'JetBrains Mono',monospace;font-size:0.9rem;font-weight:600}}
.crypto-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}}
.crypto-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px}}
.crypto-card:hover{{border-color:var(--border2)}}
.crypto-header{{display:flex;align-items:center;gap:8px;margin-bottom:8px}}
.crypto-logo{{width:28px;height:28px;border-radius:50%}}
.crypto-ticker{{font-family:'JetBrains Mono',monospace;font-size:0.85rem;font-weight:600}}
.crypto-name{{font-size:0.65rem;color:var(--muted)}}
.crypto-price{{font-family:'JetBrains Mono',monospace;font-size:1.1rem;font-weight:600;margin-bottom:8px}}
.crypto-changes{{display:flex;gap:6px;margin-bottom:6px}}
.chg-item{{flex:1;background:var(--surface2);border-radius:5px;padding:4px 6px;text-align:center}}
.chg-label{{font-size:0.58rem;text-transform:uppercase;color:var(--muted);font-family:'JetBrains Mono',monospace}}
.chg-val{{font-family:'JetBrains Mono',monospace;font-size:0.75rem;font-weight:500;margin-top:1px}}
.crypto-footer{{font-size:0.7rem;color:var(--muted);margin-top:6px}}
/* ── MACRO ── */
.macro-grid{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}}
.macro-calendar,.macro-rules{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:1rem 1.2rem}}
.macro-row{{display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--border);font-size:13px}}
.macro-row:last-child{{border-bottom:none}}
.macro-day{{font-family:'JetBrains Mono',monospace;font-size:0.72rem;color:var(--muted);min-width:80px}}
.macro-event{{flex:1;font-size:0.82rem}}
.impact-badge{{font-family:'JetBrains Mono',monospace;font-size:0.62rem;padding:2px 7px;border-radius:4px;text-transform:uppercase}}
.impact-badge.red{{background:rgba(255,71,87,0.15);color:var(--red)}}
.impact-badge.amber{{background:rgba(255,165,2,0.15);color:var(--amber)}}
.impact-badge.neutral{{background:rgba(107,114,128,0.15);color:var(--muted)}}
.rules-list{{list-style:none;display:flex;flex-direction:column;gap:6px}}
.rules-list li{{font-size:0.78rem;color:var(--muted);padding-left:14px;position:relative;line-height:1.4}}
.rules-list li::before{{content:'>';position:absolute;left:0;color:var(--amber)}}
.footer{{text-align:center;padding:1.5rem;font-size:0.68rem;color:var(--muted);border-top:1px solid var(--border);font-family:'JetBrains Mono',monospace}}
@media(max-width:640px){{
  .tab-content{{padding:1rem}}
  .indices-grid{{grid-template-columns:repeat(2,1fr)}}
  .crypto-grid{{grid-template-columns:repeat(2,1fr)}}
  .macro-grid{{grid-template-columns:1fr}}
  .expanded-grid{{grid-template-columns:1fr}}
  .signal-top{{flex-direction:column;align-items:flex-start}}
  .risk-block{{text-align:left}}
}}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1><span class="live-dot"></span>Day Trading Dashboard</h1>
    <p>NASDAQ · S&P 500 · Futuros · Crypto · Noticias — {now}</p>
  </div>
</div>
<div class="tabs">
  <button class="tab-btn active" onclick="showTab('markets')">Markets</button>
  <button class="tab-btn" onclick="showTab('stocks')">Stocks</button>
  <button class="tab-btn" onclick="showTab('crypto')">Crypto</button>
  <button class="tab-btn" onclick="showTab('macro')">Macro</button>
</div>

<div id="tab-markets" class="tab-content active">
  <div class="section-title">Sesgo de mercado NQ / ES</div>
  {sig_html}
  <div class="section-title">Indices y ETFs</div>
  <div class="indices-grid">{indices_html}</div>
  <div class="section-title" style="margin-top:0.5rem">Futuros — NQ · ES · YM · RTY · Gold · Oil</div>
  <div class="indices-grid">{futures_html}</div>
  <div class="section-title" style="margin-top:0.5rem">Noticias relevantes NQ / S&P 500</div>
  <div class="news-list">{news_html}</div>
</div>

<div id="tab-stocks" class="tab-content">
  <div class="section-title">NASDAQ Watchlist — NVDA · GOOGL · MSFT y mas</div>
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th>Empresa</th><th>Sector</th><th>Precio</th><th>Cambio</th>
        <th>Pre-mkt</th><th>Volumen</th><th>Day range</th><th>52w pos</th><th>5d chart</th><th>Senal</th>
      </tr></thead>
      <tbody>{stocks_html}</tbody>
    </table>
  </div>
  <p style="font-size:11px;color:var(--muted);margin-top:8px;font-family:'JetBrains Mono',monospace">
    Click en cualquier fila para ver niveles clave, catalizadores y setup de scalping
  </p>
</div>

<div id="tab-crypto" class="tab-content">
  <div class="section-title">Crypto — BTC · ETH · ZEC · Altcoins</div>
  {crypto_html}
</div>

<div id="tab-macro" class="tab-content">
  <div class="section-title">Macro calendario y reglas de gestion</div>
  {macro_html}
</div>

<div class="footer">
  Day Trading Dashboard · {now} · Yahoo Finance + CoinGecko + FMP ·
  No es asesoramiento financiero
</div>
<script>
function showTab(name){{
  document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  event.target.classList.add('active');
}}
function toggleRow(ticker){{
  const exp=document.getElementById('exp-'+ticker);
  if(!exp)return;
  exp.style.display=exp.style.display==='none'?'table-row':'none';
}}
</script>
</body>
</html>"""


# ─── MAIN ─────────────────────────────────────────────────────

def main():
    print("Day Trading Dashboard Generator")
    print()

    print("Fetching indices...")
    indices_data = []
    for item in INDICES:
        print(f"  {item['ticker']}...", end=" ")
        d = yf_get(item["ticker"])
        indices_data.append({**item, "data": d})
        print("OK" if d else "FAIL")
        time.sleep(0.3)

    print("\nFetching futures...")
    futures_data = fetch_futures()

    print("\nFetching stocks...")
    stocks_data = []
    for item in STOCKS:
        print(f"  {item['ticker']}...", end=" ")
        d = yf_get(item["ticker"])
        stocks_data.append({**item, "data": d})
        print("OK" if d else "FAIL")
        time.sleep(0.3)

    print("\nFetching crypto...")
    crypto_raw  = cg_get_markets()
    global_data = cg_global()
    print(f"  Got {len(crypto_raw)} coins")

    print("\nFetching news...")
    news = fetch_news()
    print(f"  Got {len(news)} news items")

    print("\nComputing signals...")
    risk          = compute_risk(indices_data, futures_data)
    market_signal = compute_market_signal(indices_data, futures_data, news)
    print(f"  Market: {market_signal['label']} (score {market_signal['score']:+d}) | Risk: {risk['level']} (VIX {risk['vix']:.1f})")

    crypto_html = build_crypto_html(crypto_raw, global_data)
    macro_html  = build_macro_html()

    print("\nGenerating HTML...")
    html = build_html(indices_data, stocks_data, crypto_html, macro_html,
                      futures_data, news, market_signal, risk)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"\nDone: {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
