#!/usr/bin/env python3
"""
S&P 500 Sector Heatmap Generator
Fuentes: Yahoo Finance (precios, returns, P/E, div yield)
"""

import json
import os
import sys
import datetime
import urllib.request
import urllib.parse
import time
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "index.html"

# ─── SECTOR DEFINITIONS ───────────────────────────────────────

SECTORS = [
    {
        "name": "Information Technology", "short": "Tech",
        "etf": "XLK", "weight_sp": 28.0,
        "top5": [
            ("NVDA", "NVIDIA",           15.1),
            ("AAPL", "Apple",            12.2),
            ("MSFT", "Microsoft",         8.8),
            ("AVGO", "Broadcom",          5.6),
            ("MU",   "Micron",            5.2),
        ],
    },
    {
        "name": "Health Care", "short": "Healthcare",
        "etf": "XLV", "weight_sp": 12.0,
        "top5": [
            ("LLY",  "Eli Lilly",        15.0),
            ("JNJ",  "J&J",              10.5),
            ("ABBV", "AbbVie",            7.0),
            ("UNH",  "UnitedHealth",      6.8),
            ("MRK",  "Merck",             5.3),
        ],
    },
    {
        "name": "Financials", "short": "Financials",
        "etf": "XLF", "weight_sp": 12.0,
        "top5": [
            ("BRK-B", "Berkshire Hathaway", 12.2),
            ("JPM",   "JPMorgan Chase",     11.1),
            ("V",     "Visa",                7.4),
            ("MA",    "Mastercard",          5.5),
            ("BAC",   "Bank of America",     4.5),
        ],
    },
    {
        "name": "Consumer Discretionary", "short": "Cons. Disc.",
        "etf": "XLY", "weight_sp": 10.0,
        "top5": [
            ("AMZN", "Amazon",       28.1),
            ("TSLA", "Tesla",        19.6),
            ("HD",   "Home Depot",    5.1),
            ("TJX",  "TJX Cos.",      3.9),
            ("MCD",  "McDonald's",    3.8),
        ],
    },
    {
        "name": "Industrials", "short": "Industrials",
        "etf": "XLI", "weight_sp": 8.9,
        "top5": [
            ("GE",  "GE Aerospace",  5.4),
            ("CAT", "Caterpillar",   3.8),
            ("RTX", "RTX Corp.",     3.3),
            ("HON", "Honeywell",     3.2),
            ("UPS", "UPS",           3.0),
        ],
    },
    {
        "name": "Communication Services", "short": "Comm. Svcs.",
        "etf": "XLC", "weight_sp": 8.8,
        "top5": [
            ("META",  "Meta",          21.9),
            ("GOOGL", "Alphabet A",    15.8),
            ("GOOG",  "Alphabet C",    14.2),
            ("NFLX",  "Netflix",        8.3),
            ("TMUS",  "T-Mobile",       4.1),
        ],
    },
    {
        "name": "Consumer Staples", "short": "Cons. Staples",
        "etf": "XLP", "weight_sp": 5.5,
        "top5": [
            ("PG",   "Procter & Gamble", 14.3),
            ("COST", "Costco",           12.8),
            ("WMT",  "Walmart",           9.8),
            ("KO",   "Coca-Cola",         8.6),
            ("PEP",  "PepsiCo",           7.2),
        ],
    },
    {
        "name": "Energy", "short": "Energy",
        "etf": "XLE", "weight_sp": 3.8,
        "top5": [
            ("XOM", "Exxon Mobil",       23.5),
            ("CVX", "Chevron",           16.4),
            ("COP", "ConocoPhillips",     7.5),
            ("EOG", "EOG Resources",      5.2),
            ("SLB", "SLB",               4.4),
        ],
    },
    {
        "name": "Utilities", "short": "Utilities",
        "etf": "XLU", "weight_sp": 2.4,
        "top5": [
            ("NEE", "NextEra Energy",        15.0),
            ("SO",  "Southern Co.",           5.7),
            ("DUK", "Duke Energy",            5.1),
            ("AEP", "Am. Electric Power",     4.4),
            ("EXC", "Exelon",                 3.8),
        ],
    },
    {
        "name": "Real Estate", "short": "Real Estate",
        "etf": "XLRE", "weight_sp": 2.3,
        "top5": [
            ("PLD",  "Prologis",        10.1),
            ("AMT",  "American Tower",   8.2),
            ("EQIX", "Equinix",          7.3),
            ("WELL", "Welltower",        6.0),
            ("PSA",  "Public Storage",   5.1),
        ],
    },
    {
        "name": "Materials", "short": "Materials",
        "etf": "XLB", "weight_sp": 2.2,
        "top5": [
            ("LIN", "Linde",              17.5),
            ("APD", "Air Products",        6.1),
            ("SHW", "Sherwin-Williams",    5.8),
            ("FCX", "Freeport-McMoRan",    5.2),
            ("NEM", "Newmont",             4.1),
        ],
    },
]

INDEX_TICKERS = [
    {"ticker": "SPY",  "name": "S&P 500"},
    {"ticker": "QQQ",  "name": "NASDAQ 100"},
    {"ticker": "IWM",  "name": "Russell 2000"},
]

# ─── DATA FETCHING ────────────────────────────────────────────

def yf_history(ticker: str) -> dict:
    """Fetch 2y weekly history + quote meta for an ETF/stock."""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}"
           f"?interval=1wk&range=2y")
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        result     = data["chart"]["result"][0]
        meta       = result["meta"]
        timestamps = result.get("timestamp", [])
        closes     = result["indicators"]["quote"][0].get("close", [])
        pairs      = [(t, c) for t, c in zip(timestamps, closes) if c is not None]

        current = meta.get("regularMarketPrice") or (pairs[-1][1] if pairs else 0)
        pe      = meta.get("trailingPE")
        div     = meta.get("dividendYield")
        w52h    = meta.get("fiftyTwoWeekHigh", 0) or 0
        w52l    = meta.get("fiftyTwoWeekLow",  0) or 0

        now   = datetime.datetime.now()
        jan1  = datetime.datetime(now.year, 1, 1).timestamp()
        ago6m = (now - datetime.timedelta(days=182)).timestamp()
        ago1y = (now - datetime.timedelta(days=365)).timestamp()

        def closest_close(ts_target):
            if not pairs:
                return None
            return min(pairs, key=lambda p: abs(p[0] - ts_target))[1]

        def pct_return(prev):
            if prev and current and prev > 0:
                return round((current - prev) / prev * 100, 2)
            return None

        p_ytd = closest_close(jan1)
        p_6m  = closest_close(ago6m)
        p_1y  = closest_close(ago1y)

        div_pct = None
        if div:
            div_pct = round(div * 100, 2) if div < 0.3 else round(div, 2)

        return {
            "price":    round(current, 2),
            "pe":       round(pe, 1) if pe else None,
            "div":      div_pct,
            "w52h":     round(w52h, 2),
            "w52l":     round(w52l, 2),
            "ytd":      pct_return(p_ytd),
            "m6":       pct_return(p_6m),
            "y1":       pct_return(p_1y),
        }
    except Exception as e:
        print(f"  WARNING yf ({ticker}): {e}", file=sys.stderr)
        return {}


# ─── SIGNAL / RATING ──────────────────────────────────────────

def momentum_rating(ytd, y1) -> tuple:
    """Returns (label, color) based on price momentum."""
    score = 0
    if ytd is not None:
        if ytd > 15:   score += 3
        elif ytd > 7:  score += 2
        elif ytd > 2:  score += 1
        elif ytd < -15: score -= 3
        elif ytd < -7:  score -= 2
        elif ytd < -2:  score -= 1
    if y1 is not None:
        if y1 > 20:   score += 2
        elif y1 > 10: score += 1
        elif y1 < -20: score -= 2
        elif y1 < -10: score -= 1

    if score >= 4:   return "STRONG OW",   "#00d4aa"
    if score >= 2:   return "OVERWEIGHT",  "#00d4aa"
    if score >= 1:   return "SLIGHT OW",   "#3b82f6"
    if score > -1:   return "NEUTRAL",     "#6b7280"
    if score > -2:   return "SLIGHT UW",   "#ffa502"
    if score > -4:   return "UNDERWEIGHT", "#ff4757"
    return              "STRONG UW",       "#ff4757"


# ─── COLOR HELPERS ────────────────────────────────────────────

def perf_color(pct) -> str:
    if pct is None:   return "#6b7280"
    if pct >= 15:     return "#00956e"
    if pct >= 7:      return "#00d4aa"
    if pct >= 2:      return "#4dcfb0"
    if pct >= -2:     return "#6b7280"
    if pct >= -7:     return "#ffa502"
    if pct >= -15:    return "#ff4757"
    return "#cc1a2e"


def perf_bg(pct) -> str:
    if pct is None:  return "rgba(107,114,128,0.04)"
    if pct >= 7:     return "rgba(0,212,170,0.08)"
    if pct >= 2:     return "rgba(0,212,170,0.04)"
    if pct >= -2:    return "rgba(107,114,128,0.04)"
    if pct >= -7:    return "rgba(255,165,2,0.05)"
    return "rgba(255,71,87,0.08)"


def chg_class(v) -> str:
    if v is None: return "neutral"
    return "up" if v > 0 else ("down" if v < 0 else "neutral")


def fmt_pct(v) -> str:
    if v is None: return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%"


# ─── HTML BUILDERS ────────────────────────────────────────────

def build_index_pills(index_data: list) -> str:
    pills = []
    for item in index_data:
        d    = item.get("data", {})
        ytd  = d.get("ytd")
        col  = perf_color(ytd)
        sign = "+" if ytd and ytd > 0 else ""
        ytd_str = f"{sign}{ytd:.2f}%" if ytd is not None else "—"
        pills.append(
            f'<div class="index-pill">'
            f'<span class="ip-name">{item["name"]}</span>'
            f'<span class="ip-etf">{item["ticker"]}</span>'
            f'<span class="ip-ytd" style="color:{col}">YTD {ytd_str}</span>'
            f'<span class="ip-price" style="color:#e8eaf0">${d.get("price", 0):,.2f}</span>'
            f'</div>'
        )
    return "\n".join(pills)


def build_legend() -> str:
    stops = [
        ("#cc1a2e", "< −15%"),
        ("#ff4757", "−15%"),
        ("#ffa502", "−7%"),
        ("#6b7280", "0%"),
        ("#4dcfb0", "+2%"),
        ("#00d4aa", "+7%"),
        ("#00956e", "+15%"),
    ]
    gradient = ", ".join(s[0] for s in stops)
    labels_html = "".join(
        f'<span style="font-size:9px;color:#6b7280;font-family:monospace">{s[1]}</span>'
        for s in stops
    )
    return f"""
<div class="legend-wrap">
  <div class="legend-label">Performance</div>
  <div class="legend-bar" style="background:linear-gradient(to right,{gradient})"></div>
  <div class="legend-ticks">{labels_html}</div>
</div>"""


def build_perf_bar(ytd, max_pct=25.0) -> str:
    if ytd is None:
        return '<div class="perf-bar-wrap"></div>'
    pct   = max(-max_pct, min(max_pct, ytd))
    color = perf_color(ytd)
    if pct >= 0:
        left  = 50
        width = pct / max_pct * 50
    else:
        width = abs(pct) / max_pct * 50
        left  = 50 - width
    return (f'<div class="perf-bar-wrap">'
            f'<div class="perf-bar-fill" style="left:{left:.1f}%;width:{width:.1f}%;background:{color}"></div>'
            f'<div class="perf-bar-center"></div>'
            f'</div>')


def build_52w_bar(price, low, high) -> str:
    if not all([price, low, high]) or high == low:
        return ""
    pct = max(0, min(100, (price - low) / (high - low) * 100))
    return (f'<div style="position:relative;height:4px;background:rgba(255,255,255,0.08);'
            f'border-radius:2px;margin:4px 0">'
            f'<div style="position:absolute;top:-3px;left:{pct:.0f}%;width:10px;height:10px;'
            f'border-radius:50%;background:#ffa502;transform:translateX(-50%);'
            f'border:1px solid rgba(0,0,0,0.3)"></div></div>'
            f'<div style="display:flex;justify-content:space-between;font-size:10px;'
            f'color:#6b7280;font-family:monospace;margin-top:2px">'
            f'<span>${low:,.2f}</span><span>${high:,.2f}</span></div>')


def build_sector_card(sector: dict, data: dict) -> str:
    etf   = sector["etf"]
    ytd   = data.get("ytd")
    m6    = data.get("m6")
    y1    = data.get("y1")
    price = data.get("price", 0)
    pe    = data.get("pe")
    div   = data.get("div")
    w52h  = data.get("w52h", 0)
    w52l  = data.get("w52l", 0)

    col    = perf_color(ytd)
    bg     = perf_bg(ytd)
    rating_label, rating_color = momentum_rating(ytd, y1)

    pe_str  = f"{pe:.1f}x" if pe else "—"
    div_str = f"{div:.2f}%" if div else "—"

    perf_bar = build_perf_bar(ytd)

    # Top 5 holdings HTML
    holdings_html = ""
    for tkr, name, wgt in sector["top5"]:
        bar_w = min(100, wgt * 3)  # scale: 33% weight = full bar
        holdings_html += f"""
        <div class="holding-row">
          <span class="holding-ticker">{tkr}</span>
          <span class="holding-name">{name}</span>
          <div class="holding-bar-wrap">
            <div class="holding-bar" style="width:{bar_w:.0f}%"></div>
          </div>
          <span class="holding-pct">{wgt:.1f}%</span>
        </div>"""

    w52_bar = build_52w_bar(price, w52l, w52h)

    # Sort data attributes
    ytd_attr  = f"{ytd:.2f}"   if ytd  is not None else "-99"
    pe_attr   = f"{pe:.1f}"    if pe   is not None else "999"
    div_attr  = f"{div:.2f}"   if div  is not None else "0"

    return f"""
<div class="sector-card" data-ytd="{ytd_attr}" data-weight="{sector['weight_sp']}"
     data-pe="{pe_attr}" data-div="{div_attr}"
     style="border-left:3px solid {col};background:{bg}">
  <div class="sc-header" onclick="toggleSector('{etf}')">
    <div class="sc-header-left">
      <div class="sc-name">{sector['name']}</div>
      <div class="sc-meta">{etf} &nbsp;·&nbsp; {sector['weight_sp']}% del S&P 500</div>
    </div>
    <div class="sc-header-right">
      <div class="sc-ytd-badge" style="color:{col};background:{col}1a">{fmt_pct(ytd)}</div>
      <div class="sc-rating" style="color:{rating_color}">{rating_label}</div>
    </div>
  </div>

  {perf_bar}

  <div class="sc-stats" onclick="toggleSector('{etf}')">
    <div class="sc-stat">
      <div class="sc-stat-lbl">Precio</div>
      <div class="sc-stat-val">${price:,.2f}</div>
    </div>
    <div class="sc-stat">
      <div class="sc-stat-lbl">P/E</div>
      <div class="sc-stat-val">{pe_str}</div>
    </div>
    <div class="sc-stat">
      <div class="sc-stat-lbl">Div</div>
      <div class="sc-stat-val">{div_str}</div>
    </div>
    <div class="sc-stat">
      <div class="sc-stat-lbl">6M</div>
      <div class="sc-stat-val {chg_class(m6)}">{fmt_pct(m6)}</div>
    </div>
    <div class="sc-stat">
      <div class="sc-stat-lbl">1Y</div>
      <div class="sc-stat-val {chg_class(y1)}">{fmt_pct(y1)}</div>
    </div>
  </div>

  <div class="sc-expanded" id="exp-{etf}" style="display:none">
    <div class="sc-exp-inner">
      <div class="sc-holdings">
        <div class="sc-exp-title">Top 5 Holdings</div>
        {holdings_html}
      </div>
      <div class="sc-range">
        <div class="sc-exp-title">Rango 52 semanas</div>
        {w52_bar}
        <div style="font-size:11px;color:#6b7280;font-family:monospace;margin-top:8px">
          Precio actual: <span style="color:#e8eaf0;font-weight:600">${price:,.2f}</span>
        </div>
      </div>
    </div>
  </div>
</div>"""


def build_html(sectors_data: list, index_data: list) -> str:
    now        = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    today      = datetime.date.today()
    pills_html  = build_index_pills(index_data)
    legend_html = build_legend()
    cards_html  = "\n".join(
        build_sector_card(s["sector"], s["data"]) for s in sectors_data
    )

    # Best/worst for summary
    with_ytd = [s for s in sectors_data if s["data"].get("ytd") is not None]
    if with_ytd:
        best  = max(with_ytd, key=lambda s: s["data"]["ytd"])
        worst = min(with_ytd, key=lambda s: s["data"]["ytd"])
        best_html  = (f'<span style="color:#00d4aa">{best["sector"]["short"]}</span> '
                      f'<span style="color:#6b7280">{fmt_pct(best["data"]["ytd"])}</span>')
        worst_html = (f'<span style="color:#ff4757">{worst["sector"]["short"]}</span> '
                      f'<span style="color:#6b7280">{fmt_pct(worst["data"]["ytd"])}</span>')
    else:
        best_html = worst_html = "—"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>S&P 500 Sector Heatmap — {today.strftime('%b %d, %Y')}</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#08090d;--surface:#0f1117;--surface2:#161820;--surface3:#1c1e28;
  --border:rgba(255,255,255,0.06);--border2:rgba(255,255,255,0.12);
  --text:#e8eaf0;--muted:#6b7280;
  --green:#00d4aa;--red:#ff4757;--amber:#ffa502;--blue:#3b82f6;
  --mono:'JetBrains Mono',monospace;--sans:'DM Sans',sans-serif;
}}
body{{background:var(--bg);color:var(--text);font-family:var(--sans);min-height:100vh}}
.up{{color:var(--green)}}.down{{color:var(--red)}}.neutral{{color:var(--muted)}}

/* ── HEADER ── */
.header{{background:var(--surface);border-bottom:1px solid var(--border);padding:1.2rem 1.5rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem}}
.header-left h1{{font-size:1.05rem;font-weight:600;display:flex;align-items:center;gap:8px}}
.live-dot{{width:7px;height:7px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;flex-shrink:0}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}
.header-left p{{font-size:0.7rem;color:var(--muted);font-family:var(--mono);margin-top:3px}}
.header-right{{display:flex;gap:1rem;flex-wrap:wrap;align-items:center}}
.summary-item{{font-family:var(--mono);font-size:0.72rem;display:flex;flex-direction:column;gap:2px}}
.summary-lbl{{font-size:0.6rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted)}}

/* ── INDEX PILLS ── */
.pills-row{{background:var(--surface);border-bottom:1px solid var(--border);padding:0.75rem 1.5rem;display:flex;gap:10px;flex-wrap:wrap;align-items:center}}
.index-pill{{background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:7px 12px;display:flex;align-items:center;gap:8px}}
.ip-name{{font-size:0.72rem;font-weight:500}}
.ip-etf{{font-family:var(--mono);font-size:0.65rem;color:var(--muted);background:rgba(255,255,255,0.05);padding:1px 5px;border-radius:3px}}
.ip-ytd{{font-family:var(--mono);font-size:0.8rem;font-weight:700}}
.ip-price{{font-family:var(--mono);font-size:0.72rem}}

/* ── CONTROLS ── */
.controls{{padding:0.75rem 1.5rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap;border-bottom:1px solid var(--border);background:var(--surface)}}
.sort-label{{font-size:0.68rem;text-transform:uppercase;letter-spacing:0.07em;color:var(--muted);font-family:var(--mono)}}
.sort-btns{{display:flex;gap:4px}}
.sort-btn{{font-size:0.75rem;padding:4px 12px;border-radius:6px;border:1px solid var(--border2);background:transparent;color:var(--muted);cursor:pointer;font-family:var(--sans);transition:all 0.15s}}
.sort-btn:hover,.sort-btn.active{{background:var(--green);color:#000;border-color:var(--green);font-weight:500}}
.legend-wrap{{margin-left:auto;display:flex;flex-direction:column;gap:3px}}
.legend-label{{font-size:0.6rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--muted);font-family:var(--mono)}}
.legend-bar{{height:8px;width:220px;border-radius:4px}}
.legend-ticks{{display:flex;justify-content:space-between;width:220px}}

/* ── SECTOR GRID ── */
.main{{padding:1.2rem 1.5rem;max-width:1400px;margin:0 auto}}
.sectors-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}

/* ── SECTOR CARD ── */
.sector-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;overflow:hidden;transition:border-color 0.2s}}
.sector-card:hover{{border-color:var(--border2)}}
.sc-header{{display:flex;justify-content:space-between;align-items:flex-start;padding:12px 14px 8px;cursor:pointer;gap:8px}}
.sc-header-left{{flex:1;min-width:0}}
.sc-name{{font-size:0.88rem;font-weight:600;line-height:1.2}}
.sc-meta{{font-family:var(--mono);font-size:0.62rem;color:var(--muted);margin-top:3px}}
.sc-header-right{{display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0}}
.sc-ytd-badge{{font-family:var(--mono);font-size:0.85rem;font-weight:700;padding:2px 8px;border-radius:5px;white-space:nowrap}}
.sc-rating{{font-family:var(--mono);font-size:0.62rem;font-weight:600;letter-spacing:0.04em}}

/* ── PERF BAR ── */
.perf-bar-wrap{{position:relative;height:4px;background:rgba(255,255,255,0.06);margin:0 14px 4px}}
.perf-bar-fill{{position:absolute;top:0;height:100%;border-radius:2px}}
.perf-bar-center{{position:absolute;left:50%;top:-3px;width:1px;height:10px;background:rgba(255,255,255,0.15)}}

/* ── STATS ── */
.sc-stats{{display:grid;grid-template-columns:repeat(5,1fr);padding:6px 14px 10px;cursor:pointer;gap:4px}}
.sc-stat{{background:var(--surface2);border-radius:5px;padding:5px 6px;text-align:center}}
.sc-stat-lbl{{font-size:0.58rem;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted);font-family:var(--mono);margin-bottom:2px}}
.sc-stat-val{{font-family:var(--mono);font-size:0.78rem;font-weight:500}}

/* ── EXPANDED ── */
.sc-expanded{{border-top:1px solid var(--border);padding:12px 14px}}
.sc-exp-inner{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
.sc-exp-title{{font-size:0.62rem;text-transform:uppercase;letter-spacing:0.07em;color:var(--green);font-family:var(--mono);font-weight:600;margin-bottom:8px}}
.sc-holdings{{display:flex;flex-direction:column;gap:5px}}
.holding-row{{display:flex;align-items:center;gap:6px;font-size:0.72rem}}
.holding-ticker{{font-family:var(--mono);font-weight:600;min-width:40px;font-size:0.68rem}}
.holding-name{{color:var(--muted);flex:1;font-size:0.68rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.holding-bar-wrap{{width:50px;height:3px;background:rgba(255,255,255,0.08);border-radius:2px;flex-shrink:0}}
.holding-bar{{height:3px;background:var(--green);border-radius:2px}}
.holding-pct{{font-family:var(--mono);font-size:0.65rem;color:var(--muted);min-width:32px;text-align:right}}

/* ── FOOTER ── */
.footer{{text-align:center;padding:1.5rem;font-size:0.65rem;color:var(--muted);border-top:1px solid var(--border);font-family:var(--mono);margin-top:2rem}}

/* ── MOBILE ── */
@media(max-width:640px){{
  .main{{padding:0.75rem 1rem}}
  .controls,.pills-row{{padding:0.75rem 1rem}}
  .sectors-grid{{grid-template-columns:1fr}}
  .sc-exp-inner{{grid-template-columns:1fr}}
  .legend-wrap{{margin-left:0}}
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-left">
    <h1><div class="live-dot"></div>S&P 500 Sector Heatmap</h1>
    <p>11 sectores GICS · ETFs · YTD · P/E · Dividendo · {now}</p>
  </div>
  <div class="header-right">
    <div class="summary-item">
      <span class="summary-lbl">Mejor sector</span>
      <span>{best_html}</span>
    </div>
    <div class="summary-item">
      <span class="summary-lbl">Peor sector</span>
      <span>{worst_html}</span>
    </div>
  </div>
</div>

<div class="pills-row">
  {pills_html}
</div>

<div class="controls">
  <span class="sort-label">Ordenar por</span>
  <div class="sort-btns">
    <button class="sort-btn active" onclick="sortCards('ytd', this)">YTD</button>
    <button class="sort-btn" onclick="sortCards('weight', this)">Peso S&P</button>
    <button class="sort-btn" onclick="sortCards('pe', this)">P/E</button>
    <button class="sort-btn" onclick="sortCards('div', this)">Dividendo</button>
  </div>
  {legend_html}
</div>

<div class="main">
  <div class="sectors-grid" id="sectors-grid">
    {cards_html}
  </div>
</div>

<div class="footer">
  S&P 500 Sector Heatmap · {now} · Datos: Yahoo Finance ·
  No es asesoramiento financiero
</div>

<script>
function toggleSector(etf) {{
  const exp = document.getElementById('exp-' + etf);
  if (!exp) return;
  exp.style.display = exp.style.display === 'none' ? 'block' : 'none';
}}

function sortCards(key, btn) {{
  document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const grid  = document.getElementById('sectors-grid');
  const cards = [...grid.querySelectorAll('.sector-card')];
  const asc   = (key === 'pe');  // P/E: lowest first; all others: highest first
  cards.sort((a, b) => {{
    const va = parseFloat(a.dataset[key] ?? 0);
    const vb = parseFloat(b.dataset[key] ?? 0);
    return asc ? va - vb : vb - va;
  }});
  cards.forEach(c => grid.appendChild(c));
}}
</script>
</body>
</html>"""


# ─── MAIN ─────────────────────────────────────────────────────

def main():
    print("S&P 500 Sector Heatmap Generator")
    print()

    print("Fetching index data (SPY, QQQ, IWM)...")
    index_data = []
    for item in INDEX_TICKERS:
        print(f"  {item['ticker']}...", end=" ")
        d = yf_history(item["ticker"])
        index_data.append({"ticker": item["ticker"], "name": item["name"], "data": d})
        print(f"OK  YTD={d.get('ytd', 'N/A')}%" if d else "FAIL")
        time.sleep(0.3)

    print("\nFetching sector ETF data...")
    sectors_data = []
    for sector in SECTORS:
        etf = sector["etf"]
        print(f"  {etf} ({sector['short']})...", end=" ")
        d = yf_history(etf)
        sectors_data.append({"sector": sector, "data": d})
        print(f"OK  YTD={d.get('ytd', 'N/A')}%" if d else "FAIL")
        time.sleep(0.3)

    print("\nGenerating HTML...")
    html = build_html(sectors_data, index_data)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"\nDone: {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
