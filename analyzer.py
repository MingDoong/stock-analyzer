"""Compute financial metrics and growth analysis from raw fetched data."""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

_REVENUE_KEYS = ["Total Revenue", "Operating Revenue", "Revenue"]
_GROSS_KEYS   = ["Gross Profit"]
_OPINC_KEYS   = ["Operating Income", "EBIT"]
_NETINC_KEYS  = ["Net Income", "Net Income Common Stockholders",
                  "Net Income From Continuing Operation Net Minority Interest"]
_OCF_KEYS     = ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities",
                  "Net Cash Provided By Operating Activities"]
_CAPEX_KEYS   = ["Capital Expenditure", "Purchase Of Property Plant And Equipment",
                  "Capital Expenditures"]
_EPS_KEYS     = ["Diluted EPS", "Basic EPS"]


def _find_row(df: pd.DataFrame, keys: List[str]) -> Optional[pd.Series]:
    if df is None or df.empty:
        return None
    for k in keys:
        if k in df.index:
            s = df.loc[k].dropna()
            return s.sort_index()
    return None


def _yoy_growth(s: pd.Series) -> pd.Series:
    return s.pct_change() * 100


def _cagr(s: pd.Series) -> Optional[float]:
    s = s.dropna()
    if len(s) < 2:
        return None
    start, end = s.iloc[0], s.iloc[-1]
    years = (s.index[-1] - s.index[0]).days / 365.25
    if start <= 0 or end <= 0 or years <= 0:
        return None
    return (end / start) ** (1 / years) - 1


def _growth_category(avg_growth: float, trend_slope: float) -> str:
    if avg_growth >= 25:
        return "고성장 가속" if trend_slope > 2 else ("고성장 둔화" if trend_slope < -2 else "고성장 안정")
    if avg_growth >= 10:
        return "중성장 가속" if trend_slope > 2 else ("중성장 둔화" if trend_slope < -2 else "중성장 안정")
    if avg_growth >= 0:
        return "저성장" if trend_slope >= -1 else "성장 둔화"
    return "역성장 회복" if trend_slope > 2 else "역성장"


def analyze_company(raw: Dict) -> Dict:
    inc = raw["income_stmt"]
    cf  = raw.get("cashflow")

    revenue = _find_row(inc, _REVENUE_KEYS)
    gross   = _find_row(inc, _GROSS_KEYS)
    opinc   = _find_row(inc, _OPINC_KEYS)
    netinc  = _find_row(inc, _NETINC_KEYS)
    eps     = _find_row(inc, _EPS_KEYS)
    ocf     = _find_row(cf,  _OCF_KEYS)
    capex   = _find_row(cf,  _CAPEX_KEYS)

    result: Dict = {
        "ticker":     raw["ticker"],
        "name":       raw["name"],
        "sector":     raw["sector"],
        "market_cap": raw["market_cap"],
        "pe_ratio":   raw.get("pe_ratio"),
        "ps_ratio":   raw.get("ps_ratio"),
        "price_history": raw.get("price_history"),
    }

    # ── Revenue ───────────────────────────────────────────────────
    if revenue is not None and len(revenue) >= 1:
        rev_growth   = _yoy_growth(revenue)
        valid_growth = rev_growth.dropna()
        avg_g  = float(valid_growth.mean()) if len(valid_growth) else 0.0
        slope  = float(np.polyfit(np.arange(len(valid_growth)), valid_growth.values, 1)[0]) if len(valid_growth) >= 3 else 0.0

        result.update({
            "revenue":         revenue,
            "revenue_growth":  rev_growth,
            "revenue_cagr":    _cagr(revenue),
            "latest_revenue":  float(revenue.iloc[-1]),
            "avg_growth":      avg_g,
            "growth_slope":    slope,
            "growth_category": _growth_category(avg_g, slope),
        })

    # ── Income ────────────────────────────────────────────────────
    if netinc is not None:
        result["net_income"]      = netinc
        result["net_income_cagr"] = _cagr(netinc)

    if eps is not None:
        result["eps"] = eps

    # ── Margins ───────────────────────────────────────────────────
    def _margin(num, denom):
        if num is None or denom is None:
            return None
        aligned = num.reindex(denom.index).dropna()
        d = denom.reindex(aligned.index)
        return (aligned / d * 100).dropna()

    result["gross_margin"]     = _margin(gross,  revenue)
    result["operating_margin"] = _margin(opinc,  revenue)
    result["net_margin"]       = _margin(netinc, revenue)

    # ── Cash flow ─────────────────────────────────────────────────
    if ocf is not None:
        result["operating_cf"] = ocf
        result["ocf_cagr"]     = _cagr(ocf)

        # FCF = Operating CF + CapEx (capex is stored as negative)
        if capex is not None:
            capex_aligned = capex.reindex(ocf.index).fillna(0)
            fcf = (ocf + capex_aligned).dropna()
            result["fcf"] = fcf
            result["fcf_cagr"] = _cagr(fcf[fcf > 0]) if (fcf > 0).any() else None

            if revenue is not None:
                fcf_margin = _margin(fcf, revenue)
                result["fcf_margin"] = fcf_margin
        else:
            result["fcf"] = ocf  # fallback: use OCF as FCF proxy

        if revenue is not None:
            result["ocf_margin"] = _margin(ocf, revenue)

    return result


def analyze_all(raw_data: Dict[str, Dict]) -> Dict[str, Dict]:
    analyses: Dict[str, Dict] = {}
    for ticker, raw in raw_data.items():
        analyses[ticker] = analyze_company(raw)

    ranked: List[Tuple[str, float]] = [
        (t, a["revenue_cagr"])
        for t, a in analyses.items()
        if a.get("revenue_cagr") is not None
    ]
    ranked.sort(key=lambda x: x[1], reverse=True)
    for rank, (ticker, _) in enumerate(ranked, 1):
        analyses[ticker]["rank"] = rank

    return analyses
