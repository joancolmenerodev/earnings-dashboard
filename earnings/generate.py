#!/usr/bin/env python3
"""
Earnings Calendar Dashboard Generator
Fetches data from Financial Modeling Prep API and generates a self-contained HTML file.
Run weekly via cron or GitHub Actions.
"""

import json
import os
import sys
import datetime
import urllib.request
import urllib.parse
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIG — edit these values
# ─────────────────────────────────────────────
FMP_API_KEY = os.getenv("FMP_API_KEY", "demo")  # set in env or replace here
OUTPUT_FILE = Path(__file__).parent / "index.html"
DAYS_AHEAD  = 90   # how many days forward to fetch
TOP_N       = 60   # max companies to show

# Extra metadata not available from FMP (add your own)
EXTRA_META = {
    "AAPL": {
        "theme": "Services margin expansion and AI device supercycle",
        "watch": [
            "iPhone 16 cycle sell-through vs analyst models",
            "Services revenue growth rate and margin trajectory",
            "India manufacturing ramp as China hedge",
            "AI feature adoption driving upgrade intent",
            "Buyback pace vs capital allocation priorities",
        ],
        "risks": ["China regulatory pressure", "Antitrust scrutiny on App Store"],
    },
    "MSFT": {
        "theme": "Azure AI acceleration and Copilot monetization",
        "watch": [
            "Azure growth rate — consensus at 34% YoY",
            "Copilot seat additions and ARPU uplift",
            "OpenAI investment drag on operating margins",
            "Gaming segment after Activision integration",
        ],
        "risks": ["AI capex overhang", "Enterprise software spending slowdown"],
    },
    "NVDA": {
        "theme": "Data center dominance and Blackwell supply ramp",
        "watch": [
            "Blackwell GPU shipment volumes and ASPs",
            "Hyperscaler capex commentary (MSFT, AMZN, GOOG, META)",
            "China revenue impact from export controls",
            "Gross margin sustainability above 74%",
            "Networking (InfiniBand/Spectrum) attach rate",
        ],
        "risks": ["Export control tightening", "AMD/custom silicon competition"],
    },
    "TSLA": {
        "theme": "Margin recovery vs volume pressure",
        "watch": [
            "Automotive gross margin ex-credits trajectory",
            "2025 delivery volume guidance vs Street at 1.8M",
            "Energy storage revenue and margin ramp",
            "FSD v13 attach rate and revenue recognition",
            "Cybertruck profitability timeline",
        ],
        "risks": ["Brand damage from CEO controversy", "BYD China market share gains"],
    },
    "META": {
        "theme": "Ad monetization efficiency and AI infrastructure ROI",
        "watch": [
            "Ad impression growth and CPM trends",
            "Llama / AI assistant engagement metrics",
            "Reality Labs losses and Vision Pro read-across",
            "Threads DAU and eventual monetization path",
        ],
        "risks": ["Regulatory privacy actions in EU", "Teen engagement regulatory risk"],
    },
    "AMZN": {
        "theme": "AWS reacceleration and retail margin normalization",
        "watch": [
            "AWS growth rate — consensus at 20% YoY",
            "Advertising revenue growth (high-margin)",
            "North America retail operating margin",
            "AI/Bedrock revenue contribution disclosure",
            "Logistics cost-per-unit trajectory",
        ],
        "risks": ["AWS pricing pressure from Azure/GCP", "Regulatory antitrust actions"],
    },
    "GOOGL": {
        "theme": "Search resilience vs AI disruption risk",
        "watch": [
            "Search revenue growth rate vs AI substitute threat",
            "YouTube ad revenue and Shorts monetization",
            "Google Cloud growth rate and profitability",
            "Gemini integration driving engagement",
            "Operating expense discipline post-restructuring",
        ],
        "risks": ["DOJ antitrust remedies", "AI Overviews impact on ad clicks"],
    },
}

DEFAULT_WATCH = [
    "Revenue growth vs consensus estimate",
    "Operating margin trajectory",
    "Management guidance for next quarter",
    "Free cash flow generation",
]
DEFAULT_RISKS = ["Macro slowdown impact", "Competitive pressure"]


# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def fmp_get(endpoint: str, params: dict = {}) -> dict | list:
    """Call FMP API and return parsed JSON."""
    base = "https://financialmodelingprep.com/stable"
    params["apikey"] = FMP_API_KEY
    qs = urllib.parse.urlencode(params)
    url = f"{base}/{endpoint}?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠ FMP error ({endpoint}): {e}", file=sys.stderr)
        return []


def fetch_earnings_calendar(days: int = 90) -> list[dict]:
    today = datetime.date.today()
    end   = today + datetime.timedelta(days=days)
    data  = fmp_get("earnings-calendar", {
        "from": today.isoformat(),
        "to":   end.isoformat(),
    })
    return data if isinstance(data, list) else []

def fetch_quote(ticker: str) -> dict:
    data = fmp_get(f"profile", {"symbol": ticker})
    if isinstance(data, list) and data:
        return data[0]
    return {}


def fetch_key_metrics(ticker: str) -> dict:
    data = fmp_get(f"key-metrics-ttm", {"symbol": ticker})
    if isinstance(data, list) and data:
        return data[0]
    return {}



def enrich_companies(raw: list[dict]) -> list[dict]:
    """Filter, sort and enrich raw FMP entries."""
    # deduplicate by ticker
    seen = {}
    for row in raw:
        t = row.get("symbol", "")
        if t and t not in seen:
            seen[t] = row

    companies = []
    tickers_to_fetch = list(seen.keys())[:TOP_N]
    total = len(tickers_to_fetch)

    for i, ticker in enumerate(tickers_to_fetch, 1):
        row = seen[ticker]
        print(f"  [{i:02d}/{total}] Enriching {ticker}...", end="\r")

        quote   = fetch_quote(ticker)
        metrics = fetch_key_metrics(ticker)
        extra   = EXTRA_META.get(ticker, {})

        eps_est      = row.get("epsEstimated")
        eps_actual   = row.get("eps")
        rev_est      = row.get("revenueEstimated")
        rev_actual   = row.get("revenue")

        surprise_pct = None
        if eps_est and eps_actual and eps_est != 0:
            surprise_pct = round((eps_actual - eps_est) / abs(eps_est) * 100, 1)

        companies.append({
            "ticker":        ticker,
            "name":          quote.get("companyName") or row.get("symbol"),
            "date":          row.get("date", ""),
            "time":          row.get("time", "").upper() or "TBD",
            "eps_est":       eps_est,
            "eps_actual":    eps_actual,
            "eps_surprise":  surprise_pct,
            "rev_est":       rev_est,
            "rev_actual":    rev_actual,
            "market_cap":    quote.get("marketCap"),
            "price":         quote.get("price"),
            "change_pct":    quote.get("changesPercentage"),
            "fwd_pe":        round(1 / metrics["earningsYieldTTM"], 1) if metrics.get("earningsYieldTTM") else None,
            "sector":        quote.get("sector") or quote.get("industry") or "—",
            "exchange":      quote.get("exchange") or "",
            "theme":         extra.get("theme", f"{ticker} quarterly results"),
            "watch":         extra.get("watch", DEFAULT_WATCH),
            "risks":         extra.get("risks", DEFAULT_RISKS),
        })

    # sort by market cap descending (largest first)
    companies.sort(key=lambda x: x.get("market_cap") or 0, reverse=True)
    print(f"\n  ✓ Enriched {len(companies)} companies")
    return companies


# ─────────────────────────────────────────────
# HTML GENERATION
# ─────────────────────────────────────────────

def fmt_num(n, prefix="", suffix="", decimals=2):
    if n is None:
        return "—"
    if abs(n) >= 1e9:
        return f"{prefix}{n/1e9:.{decimals}f}B{suffix}"
    if abs(n) >= 1e6:
        return f"{prefix}{n/1e6:.{decimals}f}M{suffix}"
    return f"{prefix}{n:.{decimals}f}{suffix}"


def week_label(date_str: str) -> str:
    try:
        d = datetime.date.fromisoformat(date_str)
        week_start = d - datetime.timedelta(days=d.weekday())
        week_end   = week_start + datetime.timedelta(days=4)
        return f"Week of {week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"
    except Exception:
        return "Unknown Week"


def days_until(date_str: str) -> int:
    try:
        d = datetime.date.fromisoformat(date_str)
        return (d - datetime.date.today()).days
    except Exception:
        return 999


def surprise_class(pct):
    if pct is None:
        return "neutral"
    if pct > 0:
        return "beat"
    if pct < 0:
        return "miss"
    return "neutral"


def generate_card(c: dict, idx: int) -> str:
    surprise   = c["eps_surprise"]
    s_class    = surprise_class(surprise)
    s_label    = f"+{surprise}%" if surprise and surprise > 0 else (f"{surprise}%" if surprise else "—")
    time_badge = "AMC" if "AMC" in c["time"] or "AFTER" in c["time"] else ("BMO" if "BMO" in c["time"] or "BEFORE" in c["time"] else c["time"])
    time_class = "amc" if time_badge == "AMC" else ("bmo" if time_badge == "BMO" else "tbd")

    try:
        d = datetime.date.fromisoformat(c["date"])
        date_fmt = d.strftime("%b %d, %Y")
    except Exception:
        date_fmt = c["date"]

    logo_url  = f"https://logo.clearbit.com/{c['ticker'].lower()}.com"
    watch_li  = "".join(f"<li>{w}</li>" for w in c["watch"])
    risks_li  = "".join(f"<li class='risk'>{r}</li>" for r in c["risks"])
    fwd_pe    = f"{c['fwd_pe']}x" if c["fwd_pe"] else "—"
    rev_str   = fmt_num(c["rev_est"], suffix="")
    eps_str   = f"${c['eps_est']:.2f}" if c["eps_est"] is not None else "—"
    change    = c.get("change_pct")
    chg_str   = f"+{change:.2f}%" if change and change > 0 else (f"{change:.2f}%" if change else "—")
    chg_class = "up" if change and change > 0 else ("down" if change and change < 0 else "")

    reported  = c["eps_actual"] is not None
    card_class = f"card {s_class}-border" if reported else "card"

    return f"""
<div class="{card_class}" data-ticker="{c['ticker']}" data-date="{c['date']}" data-sector="{c['sector']}" onclick="toggleCard(this)">
  <div class="card-header">
    <div class="card-left">
      <img class="logo" src="{logo_url}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'" alt="{c['ticker']}">
      <div class="logo-fallback" style="display:none">{c['ticker'][:2]}</div>
      <div class="card-info">
        <div class="card-name">{c['name']}</div>
        <div class="card-ticker">{c['ticker']} · <span class="sector-tag">{c['sector']}</span></div>
      </div>
    </div>
    <div class="card-right">
      <div class="date-block">
        <span class="date-str">{date_fmt}</span>
        <span class="time-badge {time_class}">{time_badge}</span>
      </div>
    </div>
  </div>

  <div class="card-metrics">
    <div class="metric">
      <div class="metric-label">EPS Est</div>
      <div class="metric-value">{eps_str}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Rev Est</div>
      <div class="metric-value">{rev_str}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Last Surprise</div>
      <div class="metric-value {s_class}">{s_label}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Fwd P/E</div>
      <div class="metric-value">{fwd_pe}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Today</div>
      <div class="metric-value {chg_class}">{chg_str}</div>
    </div>
  </div>

  <div class="theme-line">{c['theme']}</div>

  <div class="card-expanded" style="display:none">
    <div class="expanded-inner">
      <div class="watch-col">
        <div class="watch-title">What to Watch</div>
        <ul class="watch-list">{watch_li}</ul>
      </div>
      <div class="watch-col">
        <div class="watch-title risks-title">Key Risks</div>
        <ul class="watch-list">{risks_li}</ul>
      </div>
    </div>
  </div>

  <div class="card-chevron">▾</div>
</div>"""


def generate_countdown(companies: list[dict]) -> str:
    upcoming = [c for c in companies if days_until(c["date"]) >= 0]
    upcoming.sort(key=lambda x: x["date"])
    upcoming = upcoming[:5]

    items = []
    for c in upcoming:
        d = days_until(c["date"])
        logo_url = f"https://logo.clearbit.com/{c['ticker'].lower()}.com"
        label = "Today" if d == 0 else (f"{d}d" if d > 0 else "Reported")
        items.append(f"""
        <div class="countdown-item">
          <img class="cd-logo" src="{logo_url}" onerror="this.style.display='none'" alt="{c['ticker']}">
          <div class="cd-ticker">{c['ticker']}</div>
          <div class="cd-days">{label}</div>
        </div>""")

    return "\n".join(items)


def group_by_week(companies: list[dict]) -> dict:
    groups = {}
    for c in companies:
        wl = week_label(c["date"])
        groups.setdefault(wl, []).append(c)
    return groups


def build_html(companies: list[dict]) -> str:
    today     = datetime.date.today()
    quarter   = f"Q{(today.month - 1) // 3 + 1} {today.year}"
    generated = today.strftime("%B %d, %Y")
    total     = len(companies)

    beats  = sum(1 for c in companies if c["eps_surprise"] and c["eps_surprise"] > 0)
    misses = sum(1 for c in companies if c["eps_surprise"] and c["eps_surprise"] < 0)
    reported_count = beats + misses

    avg_surprise = 0.0
    if reported_count > 0:
        surprises = [c["eps_surprise"] for c in companies if c["eps_surprise"] is not None]
        avg_surprise = sum(surprises) / len(surprises) if surprises else 0.0

    countdown_html = generate_countdown(companies)
    groups         = group_by_week(companies)

    # Build sector filter options
    sectors = sorted(set(c["sector"] for c in companies if c["sector"] != "—"))
    sector_btns = "\n".join(
        f'<button class="filter-btn" onclick="filterSector(this, \'{s}\')">{s}</button>'
        for s in sectors
    )

    # Build all week sections
    sections_html = ""
    for week_lbl, week_companies in groups.items():
        cards_html = "\n".join(generate_card(c, i) for i, c in enumerate(week_companies))
        sections_html += f"""
    <div class="week-section" data-week="{week_lbl}">
      <div class="week-label">{week_lbl}</div>
      <div class="cards-grid">
        {cards_html}
      </div>
    </div>"""

    # Inline JSON for JS search
    companies_json = json.dumps([{
        "ticker": c["ticker"],
        "name": c["name"],
        "sector": c["sector"],
        "date": c["date"],
    } for c in companies])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{quarter} Earnings Calendar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg:       #08090d;
  --surface:  #0f1117;
  --surface2: #161820;
  --border:   rgba(255,255,255,0.06);
  --border2:  rgba(255,255,255,0.12);
  --text:     #e8eaf0;
  --muted:    #6b7280;
  --green:    #00d4aa;
  --red:      #ff4757;
  --amber:    #ffa502;
  --blue:     #3b82f6;
  --mono:     'JetBrains Mono', monospace;
  --sans:     'DM Sans', sans-serif;
}}

body {{ background: var(--bg); color: var(--text); font-family: var(--sans); min-height: 100vh; }}

/* ── HEADER ── */
.header {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 1.5rem 2rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; }}
.header-left h1 {{ font-size: clamp(1.4rem, 3vw, 2rem); font-weight: 600; letter-spacing: -0.02em; }}
.header-left p {{ font-size: 0.8rem; color: var(--muted); margin-top: 4px; font-family: var(--mono); }}
.kpi-strip {{ display: flex; gap: 1.5rem; flex-wrap: wrap; }}
.kpi {{ text-align: center; }}
.kpi-val {{ font-family: var(--mono); font-size: 1.2rem; font-weight: 600; }}
.kpi-lbl {{ font-size: 0.7rem; color: var(--muted); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.05em; }}
.green {{ color: var(--green); }}
.red   {{ color: var(--red); }}
.amber {{ color: var(--amber); }}

/* ── COUNTDOWN ── */
.countdown {{ background: var(--surface); border-bottom: 1px solid var(--border); padding: 1rem 2rem; overflow-x: auto; }}
.countdown-label {{ font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 0.75rem; font-family: var(--mono); }}
.countdown-strip {{ display: flex; gap: 1rem; align-items: center; }}
.countdown-item {{ display: flex; flex-direction: column; align-items: center; gap: 4px; min-width: 64px; background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; transition: border-color 0.2s; }}
.countdown-item:hover {{ border-color: var(--border2); }}
.cd-logo {{ width: 28px; height: 28px; border-radius: 6px; object-fit: contain; }}
.cd-ticker {{ font-family: var(--mono); font-size: 0.75rem; font-weight: 600; }}
.cd-days {{ font-family: var(--mono); font-size: 0.7rem; color: var(--green); }}

/* ── FILTERS ── */
.filters {{ padding: 1rem 2rem; display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; border-bottom: 1px solid var(--border); }}
.filter-btn {{ font-family: var(--sans); font-size: 0.78rem; padding: 5px 14px; border-radius: 20px; border: 1px solid var(--border2); background: transparent; color: var(--muted); cursor: pointer; transition: all 0.15s; }}
.filter-btn:hover, .filter-btn.active {{ background: var(--green); color: #000; border-color: var(--green); font-weight: 500; }}
.search-wrap {{ margin-left: auto; }}
.search-input {{ font-family: var(--mono); font-size: 0.78rem; background: var(--surface2); border: 1px solid var(--border2); color: var(--text); padding: 6px 14px; border-radius: 20px; width: 180px; outline: none; transition: border-color 0.2s; }}
.search-input:focus {{ border-color: var(--green); }}
.search-input::placeholder {{ color: var(--muted); }}

/* ── MAIN ── */
.main {{ padding: 1.5rem 2rem 4rem; max-width: 1400px; margin: 0 auto; }}
.week-section {{ margin-bottom: 2.5rem; }}
.week-label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); font-family: var(--mono); margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }}
.cards-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 12px; }}

/* ── CARD ── */
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.1rem; cursor: pointer; transition: border-color 0.2s, transform 0.1s; position: relative; }}
.card:hover {{ border-color: var(--border2); transform: translateY(-1px); }}
.beat-border {{ border-color: rgba(0,212,170,0.25); }}
.miss-border {{ border-color: rgba(255,71,87,0.25); }}
.card-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 12px; }}
.card-left {{ display: flex; align-items: center; gap: 10px; }}
.logo {{ width: 36px; height: 36px; border-radius: 8px; object-fit: contain; background: var(--surface2); }}
.logo-fallback {{ width: 36px; height: 36px; border-radius: 8px; background: var(--surface2); align-items: center; justify-content: center; font-family: var(--mono); font-size: 0.7rem; font-weight: 600; color: var(--muted); border: 1px solid var(--border2); }}
.card-name {{ font-size: 0.9rem; font-weight: 500; line-height: 1.2; }}
.card-ticker {{ font-family: var(--mono); font-size: 0.72rem; color: var(--muted); margin-top: 2px; }}
.sector-tag {{ color: var(--amber); }}
.card-right {{ text-align: right; flex-shrink: 0; }}
.date-str {{ font-family: var(--mono); font-size: 0.72rem; color: var(--muted); display: block; }}
.time-badge {{ font-family: var(--mono); font-size: 0.65rem; font-weight: 600; padding: 2px 7px; border-radius: 4px; margin-top: 4px; display: inline-block; }}
.time-badge.amc {{ background: rgba(0,212,170,0.15); color: var(--green); }}
.time-badge.bmo {{ background: rgba(59,130,246,0.15); color: var(--blue); }}
.time-badge.tbd {{ background: rgba(107,114,128,0.15); color: var(--muted); }}

/* ── METRICS ── */
.card-metrics {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 10px; }}
.metric {{ background: var(--surface2); border-radius: 6px; padding: 6px 8px; }}
.metric-label {{ font-size: 0.6rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 3px; }}
.metric-value {{ font-family: var(--mono); font-size: 0.78rem; font-weight: 500; }}
.beat {{ color: var(--green); }}
.miss {{ color: var(--red); }}
.neutral {{ color: var(--muted); }}
.up {{ color: var(--green); }}
.down {{ color: var(--red); }}

/* ── THEME ── */
.theme-line {{ font-size: 0.78rem; color: var(--muted); font-style: italic; margin-bottom: 4px; line-height: 1.4; }}

/* ── EXPANDED ── */
.card-expanded {{ margin-top: 12px; border-top: 1px solid var(--border); padding-top: 12px; }}
.expanded-inner {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
.watch-title {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--green); font-family: var(--mono); margin-bottom: 8px; font-weight: 600; }}
.risks-title {{ color: var(--red); }}
.watch-list {{ list-style: none; display: flex; flex-direction: column; gap: 5px; }}
.watch-list li {{ font-size: 0.78rem; color: var(--muted); padding-left: 12px; position: relative; line-height: 1.4; }}
.watch-list li::before {{ content: '→'; position: absolute; left: 0; color: var(--green); font-size: 0.65rem; top: 1px; }}
.watch-list li.risk::before {{ color: var(--red); content: '↳'; }}

/* ── CHEVRON ── */
.card-chevron {{ text-align: center; font-size: 0.7rem; color: var(--border2); margin-top: 6px; transition: transform 0.2s; }}
.card.open .card-chevron {{ transform: rotate(180deg); }}

/* ── FOOTER ── */
.footer {{ text-align: center; padding: 2rem; font-size: 0.72rem; color: var(--muted); border-top: 1px solid var(--border); font-family: var(--mono); }}

/* ── NO RESULTS ── */
.no-results {{ text-align: center; padding: 3rem; color: var(--muted); font-family: var(--mono); display: none; }}

/* ── MOBILE ── */
@media (max-width: 640px) {{
  .header {{ padding: 1rem; }}
  .filters, .main {{ padding: 0.75rem 1rem; }}
  .countdown {{ padding: 0.75rem 1rem; }}
  .cards-grid {{ grid-template-columns: 1fr; }}
  .card-metrics {{ grid-template-columns: repeat(3, 1fr); }}
  .expanded-inner {{ grid-template-columns: 1fr; }}
  .kpi-strip {{ gap: 1rem; }}
  .search-wrap {{ margin-left: 0; width: 100%; }}
  .search-input {{ width: 100%; }}
}}
</style>
</head>
<body>

<header class="header">
  <div class="header-left">
    <h1>📅 {quarter} Earnings Season</h1>
    <p>Updated {generated} · {total} companies tracked · Data via Financial Modeling Prep</p>
  </div>
  <div class="kpi-strip">
    <div class="kpi">
      <div class="kpi-val">{total}</div>
      <div class="kpi-lbl">Companies</div>
    </div>
    <div class="kpi">
      <div class="kpi-val green">{beats}</div>
      <div class="kpi-lbl">Beats</div>
    </div>
    <div class="kpi">
      <div class="kpi-val red">{misses}</div>
      <div class="kpi-lbl">Misses</div>
    </div>
    <div class="kpi">
      <div class="kpi-val {'green' if avg_surprise >= 0 else 'red'}">{avg_surprise:+.1f}%</div>
      <div class="kpi-lbl">Avg Surprise</div>
    </div>
  </div>
</header>

<div class="countdown">
  <div class="countdown-label">Next 5 reporting</div>
  <div class="countdown-strip">
    {countdown_html}
  </div>
</div>

<div class="filters">
  <button class="filter-btn active" onclick="filterSector(this, 'all')">All</button>
  {sector_btns}
  <div class="search-wrap">
    <input class="search-input" type="text" placeholder="Search ticker or name..." oninput="searchCards(this.value)">
  </div>
</div>

<main class="main">
  {sections_html}
  <div class="no-results" id="no-results">No companies match your filter.</div>
</main>

<footer class="footer">
  {quarter} Earnings Calendar · Generated {generated} · Data: Financial Modeling Prep API ·
  Not investment advice · Past performance does not guarantee future results
</footer>

<script>
const companies = {companies_json};

function toggleCard(card) {{
  const expanded = card.querySelector('.card-expanded');
  const isOpen   = card.classList.contains('open');
  card.classList.toggle('open', !isOpen);
  expanded.style.display = isOpen ? 'none' : 'block';
}}

function filterSector(btn, sector) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.card').forEach(card => {{
    const match = sector === 'all' || card.dataset.sector === sector;
    card.style.display = match ? '' : 'none';
  }});
  updateWeekVisibility();
  checkNoResults();
}}

function searchCards(query) {{
  const q = query.toLowerCase().trim();
  document.querySelectorAll('.card').forEach(card => {{
    const ticker = (card.dataset.ticker || '').toLowerCase();
    const name   = card.querySelector('.card-name')?.textContent.toLowerCase() || '';
    card.style.display = (!q || ticker.includes(q) || name.includes(q)) ? '' : 'none';
  }});
  updateWeekVisibility();
  checkNoResults();
}}

function updateWeekVisibility() {{
  document.querySelectorAll('.week-section').forEach(section => {{
    const visible = [...section.querySelectorAll('.card')].some(c => c.style.display !== 'none');
    section.style.display = visible ? '' : 'none';
  }});
}}

function checkNoResults() {{
  const anyVisible = [...document.querySelectorAll('.card')].some(c => c.style.display !== 'none');
  document.getElementById('no-results').style.display = anyVisible ? 'none' : 'block';
}}
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print(f"🚀 Earnings Dashboard Generator")
    print(f"   API key: {'set ✓' if FMP_API_KEY != 'demo' else 'using demo (limited data)'}")
    print(f"   Output:  {OUTPUT_FILE}")
    print()

    print("📡 Fetching earnings calendar...")
    raw = fetch_earnings_calendar(DAYS_AHEAD)
    print(f"   Found {len(raw)} raw entries")

    if not raw:
        print("⚠  No data returned. Check your FMP_API_KEY.", file=sys.stderr)
        sys.exit(1)

    print("\n🔍 Enriching company data...")
    companies = enrich_companies(raw)

    print("\n🎨 Generating HTML...")
    html = build_html(companies)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"\n✅ Dashboard saved to: {OUTPUT_FILE}")
    print(f"   Companies: {len(companies)}")
    print(f"   File size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()