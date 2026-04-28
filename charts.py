"""Build interactive Plotly HTML dashboard and print rich console summary."""

from typing import Dict
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from rich.console import Console
from rich.table import Table

PALETTE = [
    "#4cc9f0", "#f72585", "#7209b7", "#4361ee", "#4895ef",
    "#00b4d8", "#90e0ef", "#f4a261", "#e76f51", "#2a9d8f",
]

CATEGORY_COLOR = {
    "고성장 가속":  "#4cc9f0",
    "고성장 안정":  "#4361ee",
    "고성장 둔화":  "#90e0ef",
    "중성장 가속":  "#2a9d8f",
    "중성장 안정":  "#7cba8d",
    "중성장 둔화":  "#f4a261",
    "저성장":      "#e9c46a",
    "성장 둔화":   "#e76f51",
    "역성장 회복":  "#f72585",
    "역성장":      "#d62828",
}


def _fmt_b(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    return f"${val / 1e9:.2f}B"


def _fmt_pct(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    return f"{val:.1f}%"


def _last(series) -> float | None:
    if series is None or len(series) == 0:
        return None
    v = series.iloc[-1]
    return float(v) if not np.isnan(v) else None


def print_summary(theme_name: str, analyses: Dict, console: Console) -> None:
    table = Table(
        title=f"[bold]{theme_name}[/bold] — 재무 성장 요약",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("순위", justify="center", width=5)
    table.add_column("Ticker", style="bold cyan", width=7)
    table.add_column("회사명", width=26)
    table.add_column("매출 CAGR", justify="right", width=10)
    table.add_column("최근 매출", justify="right", width=12)
    table.add_column("영업이익률", justify="right", width=10)
    table.add_column("순이익률",  justify="right", width=9)
    table.add_column("성장 패턴", width=14)

    sorted_items = sorted(
        analyses.items(),
        key=lambda x: x[1].get("revenue_cagr") or -999,
        reverse=True,
    )

    for ticker, a in sorted_items:
        cagr   = a.get("revenue_cagr")
        om     = _last(a.get("operating_margin"))
        nm     = _last(a.get("net_margin"))
        rank   = a.get("rank", "-")
        cat    = a.get("growth_category", "N/A")
        color  = CATEGORY_COLOR.get(cat, "white")

        table.add_row(
            str(rank),
            ticker,
            (a.get("name") or "")[:26],
            _fmt_pct(cagr * 100) if cagr else "N/A",
            _fmt_b(a.get("latest_revenue")),
            _fmt_pct(om),
            _fmt_pct(nm),
            f"[{color}]{cat}[/{color}]",
        )

    console.print(table)


def build_summary_df(analyses: Dict) -> pd.DataFrame:
    """Return summary as a pandas DataFrame (for Streamlit or export)."""
    rows = []
    sorted_items = sorted(
        analyses.items(),
        key=lambda x: x[1].get("revenue_cagr") or -999,
        reverse=True,
    )
    for ticker, a in sorted_items:
        cagr = a.get("revenue_cagr")
        om   = _last(a.get("operating_margin"))
        nm   = _last(a.get("net_margin"))
        rows.append({
            "순위":      a.get("rank", "-"),
            "Ticker":   ticker,
            "회사명":    (a.get("name") or "")[:32],
            "매출 CAGR": _fmt_pct(cagr * 100) if cagr else "N/A",
            "최근 매출":  _fmt_b(a.get("latest_revenue")),
            "영업이익률":  _fmt_pct(om),
            "순이익률":   _fmt_pct(nm),
            "성장 패턴":  a.get("growth_category", "N/A"),
        })
    return pd.DataFrame(rows)


def build_figure(theme_name: str, analyses: Dict) -> go.Figure:
    """Return the Plotly dashboard figure (used by CLI and Streamlit)."""
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=[
            "연간 매출 추이 ($B)",
            "매출 YoY 성장률 (%)",
            "순이익 추이 ($B)",
            "영업이익률 추이 (%)",
            "매출총이익률 추이 (%)",
            "매출 CAGR 순위 (%)",
        ],
        vertical_spacing=0.11,
        horizontal_spacing=0.07,
    )

    tickers = list(analyses.keys())

    for i, ticker in enumerate(tickers):
        a     = analyses[ticker]
        color = PALETTE[i % len(PALETTE)]
        name  = a.get("name", ticker)

        hover_name = f"<b>{ticker}</b> ({name})"

        # ── Revenue trend ──────────────────────────────────────────
        if "revenue" in a:
            rev = a["revenue"].dropna()
            fig.add_trace(go.Scatter(
                x=rev.index.strftime("%Y"),
                y=rev.values / 1e9,
                name=ticker,
                line=dict(color=color, width=2),
                legendgroup=ticker,
                showlegend=True,
                hovertemplate=f"{hover_name}<br>%{{x}}: $%{{y:.2f}}B<extra></extra>",
            ), row=1, col=1)

        # ── Revenue YoY growth bars ────────────────────────────────
        if "revenue_growth" in a:
            g = a["revenue_growth"].dropna()
            fig.add_trace(go.Bar(
                x=g.index.strftime("%Y"),
                y=g.values,
                name=ticker,
                marker_color=color,
                legendgroup=ticker,
                showlegend=False,
                hovertemplate=f"{hover_name}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
            ), row=1, col=2)

        # ── Net income ────────────────────────────────────────────
        if "net_income" in a:
            ni = a["net_income"].dropna()
            fig.add_trace(go.Scatter(
                x=ni.index.strftime("%Y"),
                y=ni.values / 1e9,
                name=ticker,
                line=dict(color=color, width=2, dash="dot"),
                legendgroup=ticker,
                showlegend=False,
                hovertemplate=f"{hover_name}<br>%{{x}}: $%{{y:.2f}}B<extra></extra>",
            ), row=2, col=1)

        # ── Operating margin ──────────────────────────────────────
        if "operating_margin" in a:
            om = a["operating_margin"].dropna()
            fig.add_trace(go.Scatter(
                x=om.index.strftime("%Y"),
                y=om.values,
                name=ticker,
                line=dict(color=color, width=2),
                legendgroup=ticker,
                showlegend=False,
                hovertemplate=f"{hover_name}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
            ), row=2, col=2)

        # ── Gross margin ──────────────────────────────────────────
        if "gross_margin" in a:
            gm = a["gross_margin"].dropna()
            fig.add_trace(go.Scatter(
                x=gm.index.strftime("%Y"),
                y=gm.values,
                name=ticker,
                line=dict(color=color, width=2, dash="dash"),
                legendgroup=ticker,
                showlegend=False,
                hovertemplate=f"{hover_name}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
            ), row=3, col=1)

    # ── CAGR ranking bar ──────────────────────────────────────────
    cagr_items = [
        (t, a["revenue_cagr"] * 100, a.get("name", t))
        for t, a in analyses.items()
        if a.get("revenue_cagr") is not None
    ]
    cagr_items.sort(key=lambda x: x[1], reverse=True)

    if cagr_items:
        bar_colors = [PALETTE[i % len(PALETTE)] for i in range(len(cagr_items))]
        fig.add_trace(go.Bar(
            x=[d[0] for d in cagr_items],
            y=[d[1] for d in cagr_items],
            marker_color=bar_colors,
            text=[f"{d[1]:.1f}%" for d in cagr_items],
            textposition="outside",
            showlegend=False,
            hovertemplate="<b>%{x}</b><br>Revenue CAGR: %{y:.1f}%<extra></extra>",
        ), row=3, col=2)

    # ── Layout ────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text=f"<b>{theme_name} — 재무 성장 분석 대시보드</b>",
            font=dict(size=20),
            x=0.5,
        ),
        height=1150,
        template="plotly_dark",
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        hovermode="x",
    )

    fig.update_yaxes(title_text="Revenue ($B)",    row=1, col=1)
    fig.update_yaxes(title_text="Growth (%)",      row=1, col=2)
    fig.update_yaxes(title_text="Net Income ($B)", row=2, col=1)
    fig.update_yaxes(title_text="Margin (%)",      row=2, col=2)
    fig.update_yaxes(title_text="Margin (%)",      row=3, col=1)
    fig.update_yaxes(title_text="CAGR (%)",        row=3, col=2)

    return fig


def build_cashflow_figure(theme_name: str, analyses: Dict) -> go.Figure:
    """Cash flow dashboard: Operating CF, FCF, FCF margin."""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "영업현금흐름 (Operating CF, $B)",
            "잉여현금흐름 (FCF, $B)",
            "FCF 마진 (%)",
            "영업CF 마진 (%)",
        ],
        vertical_spacing=0.14,
        horizontal_spacing=0.08,
    )

    for i, (ticker, a) in enumerate(analyses.items()):
        color = PALETTE[i % len(PALETTE)]
        name  = a.get("name", ticker)
        hn    = f"<b>{ticker}</b> ({name})"

        if "operating_cf" in a:
            ocf = a["operating_cf"].dropna()
            fig.add_trace(go.Scatter(
                x=ocf.index.strftime("%Y"), y=ocf.values / 1e9,
                name=ticker, line=dict(color=color, width=2),
                legendgroup=ticker, showlegend=True,
                hovertemplate=f"{hn}<br>%{{x}}: $%{{y:.2f}}B<extra></extra>",
            ), row=1, col=1)

        if "fcf" in a:
            fcf = a["fcf"].dropna()
            fig.add_trace(go.Bar(
                x=fcf.index.strftime("%Y"), y=fcf.values / 1e9,
                name=ticker, marker_color=color,
                legendgroup=ticker, showlegend=False,
                hovertemplate=f"{hn}<br>%{{x}}: $%{{y:.2f}}B<extra></extra>",
            ), row=1, col=2)

        if "fcf_margin" in a and a["fcf_margin"] is not None:
            fm = a["fcf_margin"].dropna()
            fig.add_trace(go.Scatter(
                x=fm.index.strftime("%Y"), y=fm.values,
                name=ticker, line=dict(color=color, width=2, dash="dash"),
                legendgroup=ticker, showlegend=False,
                hovertemplate=f"{hn}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
            ), row=2, col=1)

        if "ocf_margin" in a and a["ocf_margin"] is not None:
            om = a["ocf_margin"].dropna()
            fig.add_trace(go.Scatter(
                x=om.index.strftime("%Y"), y=om.values,
                name=ticker, line=dict(color=color, width=2),
                legendgroup=ticker, showlegend=False,
                hovertemplate=f"{hn}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
            ), row=2, col=2)

    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=1, col=2)
    fig.add_hline(y=0, line_dash="dot", line_color="gray", row=2, col=1)

    fig.update_layout(
        title=dict(text=f"<b>{theme_name} — 현금흐름 분석</b>", font=dict(size=18), x=0.5),
        height=700, template="plotly_dark", barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x",
    )
    fig.update_yaxes(title_text="Cash Flow ($B)", row=1, col=1)
    fig.update_yaxes(title_text="FCF ($B)",       row=1, col=2)
    fig.update_yaxes(title_text="FCF Margin (%)", row=2, col=1)
    fig.update_yaxes(title_text="OCF Margin (%)", row=2, col=2)
    return fig


def build_price_figure(theme_name: str, analyses: Dict) -> go.Figure:
    """Normalized price comparison (base=100) + individual price charts."""
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=[
            "정규화 주가 비교 (시작일 = 100)",
            "절대 주가 ($)",
        ],
        vertical_spacing=0.12,
    )

    for i, (ticker, a) in enumerate(analyses.items()):
        hist = a.get("price_history")
        if hist is None or hist.empty:
            continue
        color = PALETTE[i % len(PALETTE)]
        name  = a.get("name", ticker)
        close = hist["Close"].dropna()

        # Normalized
        norm = close / close.iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=close.index, y=norm.values,
            name=ticker, line=dict(color=color, width=2),
            legendgroup=ticker, showlegend=True,
            hovertemplate=f"<b>{ticker}</b><br>%{{x|%Y-%m}}: %{{y:.1f}}<extra></extra>",
        ), row=1, col=1)

        # Absolute
        fig.add_trace(go.Scatter(
            x=close.index, y=close.values,
            name=ticker, line=dict(color=color, width=2, dash="dot"),
            legendgroup=ticker, showlegend=False,
            hovertemplate=f"<b>{ticker}</b><br>%{{x|%Y-%m}}: $%{{y:.2f}}<extra></extra>",
        ), row=2, col=1)

    fig.add_hline(y=100, line_dash="dot", line_color="gray", row=1, col=1)

    fig.update_layout(
        title=dict(text=f"<b>{theme_name} — 주가 추이 (5년)</b>", font=dict(size=18), x=0.5),
        height=750, template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    fig.update_yaxes(title_text="정규화 지수", row=1, col=1)
    fig.update_yaxes(title_text="주가 ($)",   row=2, col=1)
    return fig


def create_dashboard(theme_name: str, analyses: Dict, output_path: str, console: Console) -> None:
    """CLI: print rich table + save HTML."""
    print_summary(theme_name, analyses, console)
    fig = build_figure(theme_name, analyses)
    fig.write_html(output_path, include_plotlyjs="cdn")
