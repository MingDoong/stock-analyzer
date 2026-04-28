"""Fetch financial data from Yahoo Finance via yfinance."""

from typing import Dict, List, Optional
import yfinance as yf
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn


def _get_income_stmt(ticker_obj: yf.Ticker) -> Optional[pd.DataFrame]:
    for attr in ("income_stmt", "financials"):
        try:
            df = getattr(ticker_obj, attr)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    return None


def _get_cashflow(ticker_obj: yf.Ticker) -> Optional[pd.DataFrame]:
    for attr in ("cashflow", "cash_flow"):
        try:
            df = getattr(ticker_obj, attr)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    return None


def fetch_company(ticker: str) -> Optional[Dict]:
    """Fetch annual financial + price data for a single ticker."""
    try:
        stock = yf.Ticker(ticker)
        income = _get_income_stmt(stock)
        if income is None:
            return None

        info = stock.info or {}

        # Monthly price history for 5 years
        price_hist = stock.history(period="5y", interval="1mo")
        price_hist = price_hist[["Close"]].dropna() if not price_hist.empty else None

        return {
            "ticker":        ticker,
            "name":          info.get("longName") or info.get("shortName") or ticker,
            "sector":        info.get("sector", "N/A"),
            "industry":      info.get("industry", "N/A"),
            "market_cap":    info.get("marketCap"),
            "pe_ratio":      info.get("trailingPE"),
            "ps_ratio":      info.get("priceToSalesTrailing12Months"),
            "income_stmt":   income,
            "balance_sheet": stock.balance_sheet,
            "cashflow":      _get_cashflow(stock),
            "price_history": price_hist,
        }
    except Exception:
        return None


def fetch_theme_data(tickers: List[str], console: Console) -> Dict[str, Dict]:
    """Fetch data for all tickers; skip failures silently."""
    results: Dict[str, Dict] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Fetching financial data ...", total=len(tickers))
        for ticker in tickers:
            progress.update(task, description=f"Fetching [cyan]{ticker}[/cyan] ...")
            data = fetch_company(ticker)
            if data:
                results[ticker] = data
            else:
                console.print(f"  [yellow]⚠  No data for {ticker} — skipped[/yellow]")
            progress.advance(task)

    return results
