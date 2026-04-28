"""Fetch financial data from Financial Modeling Prep (FMP) API."""

import time
from typing import Dict, List, Optional

import pandas as pd
import requests
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

BASE_URL = "https://financialmodelingprep.com/api/v3"


def _get(endpoint: str, api_key: str, params: dict = None) -> list | dict:
    url = f"{BASE_URL}/{endpoint}"
    p = {"apikey": api_key}
    if params:
        p.update(params)
    r = requests.get(url, params=p, timeout=15)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "Error Message" in data:
        raise ValueError(data["Error Message"])
    return data


def _to_df(records: list, field_map: dict) -> pd.DataFrame:
    """FMP records(list) → DataFrame (rows=metrics, cols=dates)."""
    if not records:
        return pd.DataFrame()
    rows = {}
    for name, key in field_map.items():
        rows[name] = {pd.Timestamp(r["date"]): r.get(key) for r in records}
    df = pd.DataFrame(rows).T
    df.columns = pd.to_datetime(df.columns)
    return df.astype(float, errors="ignore")


def fetch_company(ticker: str, api_key: str) -> Optional[Dict]:
    """Fetch annual financial + price data for a single ticker via FMP."""
    try:
        profile_raw = _get(f"profile/{ticker}", api_key)
        profile = profile_raw[0] if profile_raw else {}

        income_raw = _get(f"income-statement/{ticker}", api_key, {"limit": 5})
        if not income_raw:
            return None

        cf_raw = _get(f"cash-flow-statement/{ticker}", api_key, {"limit": 5})

        price_raw = _get(
            f"historical-price-full/{ticker}", api_key,
            {"serietype": "line", "from": "2019-01-01"}
        )

        # ── Income statement ──────────────────────────────────────
        income_df = _to_df(income_raw, {
            "Total Revenue":    "revenue",
            "Gross Profit":     "grossProfit",
            "Operating Income": "operatingIncome",
            "Net Income":       "netIncome",
            "Diluted EPS":      "epsdiluted",
        })

        # ── Cash flow ─────────────────────────────────────────────
        cf_df = _to_df(cf_raw, {
            "Operating Cash Flow": "operatingCashFlow",
            "Capital Expenditure": "capitalExpenditure",
            "Free Cash Flow":      "freeCashFlow",
        })

        # ── Price history (monthly, 5y) ───────────────────────────
        price_hist = None
        if isinstance(price_raw, dict) and "historical" in price_raw:
            hist = price_raw["historical"]
            series = pd.Series(
                {pd.Timestamp(r["date"]): float(r["close"]) for r in hist}
            ).sort_index()
            monthly = series.resample("ME").last().to_frame("Close")
            cutoff = pd.Timestamp.now() - pd.DateOffset(years=5)
            price_hist = monthly[monthly.index >= cutoff].dropna()

        return {
            "ticker":        ticker,
            "name":          profile.get("companyName", ticker),
            "sector":        profile.get("sector", "N/A"),
            "industry":      profile.get("industry", "N/A"),
            "market_cap":    profile.get("mktCap"),
            "pe_ratio":      profile.get("pe"),
            "ps_ratio":      profile.get("priceToSalesRatio"),
            "income_stmt":   income_df,
            "cashflow":      cf_df,
            "balance_sheet": pd.DataFrame(),
            "price_history": price_hist,
        }
    except Exception as e:
        return {"_error": str(e), "ticker": ticker}


def fetch_theme_data(tickers: List[str], api_key: str, console: Console) -> Dict[str, Dict]:
    results: Dict[str, Dict] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Fetching ...", total=len(tickers))
        for ticker in tickers:
            progress.update(task, description=f"Fetching [cyan]{ticker}[/cyan] ...")
            data = fetch_company(ticker, api_key)
            if data:
                results[ticker] = data
            else:
                console.print(f"  [yellow]⚠  No data for {ticker}[/yellow]")
            progress.advance(task)
            time.sleep(0.2)

    return results
