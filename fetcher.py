"""Fetch financial data from Yahoo Finance via yfinance + curl_cffi session."""

import time
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn


def _make_session():
    """curl_cffi로 실제 Chrome처럼 요청 — 클라우드 IP 차단 우회."""
    from curl_cffi import requests as crequests
    return crequests.Session(impersonate="chrome110")


def _get_income_stmt(stock: yf.Ticker) -> Optional[pd.DataFrame]:
    for attr in ("income_stmt", "financials"):
        try:
            df = getattr(stock, attr)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    return None


def _get_cashflow(stock: yf.Ticker) -> Optional[pd.DataFrame]:
    for attr in ("cashflow", "cash_flow"):
        try:
            df = getattr(stock, attr)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    return None


def fetch_company(ticker: str) -> Optional[Dict]:
    """Fetch annual financial + price data for a single ticker."""
    try:
        session = _make_session()
        stock   = yf.Ticker(ticker, session=session)

        income = _get_income_stmt(stock)
        if income is None:
            return {"_error": "income statement 없음", "ticker": ticker}

        info = {}
        try:
            info = stock.info or {}
        except Exception:
            pass

        price_hist = None
        try:
            ph = stock.history(period="5y", interval="1mo")
            if not ph.empty:
                price_hist = ph[["Close"]].dropna()
        except Exception:
            pass

        cf = None
        try:
            cf = _get_cashflow(stock)
        except Exception:
            pass

        return {
            "ticker":        ticker,
            "name":          info.get("longName") or info.get("shortName") or ticker,
            "sector":        info.get("sector", "N/A"),
            "industry":      info.get("industry", "N/A"),
            "market_cap":    info.get("marketCap"),
            "pe_ratio":      info.get("trailingPE"),
            "ps_ratio":      info.get("priceToSalesTrailing12Months"),
            "income_stmt":   income,
            "cashflow":      cf,
            "balance_sheet": pd.DataFrame(),
            "price_history": price_hist,
        }
    except Exception as e:
        return {"_error": str(e), "ticker": ticker}


def fetch_theme_data(tickers: List[str], console: Console) -> Dict[str, Dict]:
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
            data = fetch_company(ticker)
            if data and "_error" not in data:
                results[ticker] = data
            else:
                err = (data or {}).get("_error", "unknown")
                console.print(f"  [yellow]⚠  {ticker}: {err}[/yellow]")
            progress.advance(task)
            time.sleep(0.3)
    return results
