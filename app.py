"""Streamlit web app — US Stock Theme Analyzer."""

from datetime import datetime

import pandas as pd
import streamlit as st

from analyzer import analyze_all
from charts import (
    build_cashflow_figure,
    build_figure,
    build_price_figure,
    build_summary_df,
)
from fetcher import fetch_company
from themes import THEMES

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="📈 Stock Theme Analyzer",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.2rem; }
    .stButton > button { width: 100%; font-size: 1.05rem; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []       # list of saved analysis dicts
if "current" not in st.session_state:
    st.session_state.current = None     # currently displayed analysis


# ── Sidebar — analysis history ────────────────────────────────────────────────
with st.sidebar:
    st.header("📂 분석 기록")

    if not st.session_state.history:
        st.caption("아직 저장된 분석이 없습니다.")
    else:
        for idx, saved in enumerate(reversed(st.session_state.history)):
            label = f"**{saved['theme']}**  \n{saved['time']} · {len(saved['tickers'])}종목"
            if st.button(label, key=f"hist_{idx}", use_container_width=True):
                st.session_state.current = saved

        st.divider()
        if st.button("🗑 기록 전체 삭제", use_container_width=True):
            st.session_state.history = []
            st.session_state.current = None
            st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📈 Stock Theme Analyzer")
st.caption("테마를 선택하면 수익성·현금흐름·주가를 한눈에 분석합니다.")
st.divider()

# ── Controls ──────────────────────────────────────────────────────────────────
theme_labels = {v["name"]: k for k, v in THEMES.items()}
theme_names  = list(theme_labels.keys())

col_sel, col_top = st.columns([3, 1])
with col_sel:
    chosen_name = st.selectbox(
        "테마 선택",
        theme_names,
        index=theme_names.index("Artificial Intelligence"),
    )
with col_top:
    top_n = st.slider("종목 수", 3, 10, 7)

with st.expander("✏️ 직접 종목 입력 (선택사항)"):
    custom_raw   = st.text_input("티커 (쉼표/공백 구분)", placeholder="AAPL, MSFT, GOOGL")
    custom_label = st.text_input("테마 이름 (선택)",      placeholder="내 포트폴리오")

run_btn = st.button("🚀 분석 시작", type="primary", use_container_width=True)


# ── Cached fetch per ticker ───────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_cached(ticker: str):
    return fetch_company(ticker)


def fetch_with_progress(tickers: list) -> dict:
    bar    = st.progress(0, text="데이터 수집 중...")
    status = st.empty()
    results = {}
    for i, ticker in enumerate(tickers):
        status.caption(f"📡 {ticker} 수집 중 ({i + 1}/{len(tickers)})")
        data = _fetch_cached(ticker)
        if data and "_error" not in data:
            results[ticker] = data
        elif data and "_error" in data:
            st.error(f"❌ {ticker} 오류: {data['_error']}")
        else:
            st.warning(f"⚠️ {ticker} 데이터 없음 — 건너뜀")
        bar.progress((i + 1) / len(tickers), text=f"수집 중... {i + 1}/{len(tickers)}")
    bar.empty()
    status.empty()
    return results


# ── Run analysis ──────────────────────────────────────────────────────────────
if run_btn:
    if custom_raw.strip():
        tickers    = [t.strip().upper() for t in custom_raw.replace(",", " ").split() if t.strip()]
        theme_name = custom_label.strip() or "Custom"
    else:
        key        = theme_labels[chosen_name]
        tickers    = THEMES[key]["tickers"][:top_n]
        theme_name = THEMES[key]["name"]

    st.info(f"**{theme_name}** — {', '.join(tickers)}", icon="🔍")

    raw_data = fetch_with_progress(tickers)
    if not raw_data:
        st.error("데이터를 가져오지 못했습니다.")
        st.stop()

    with st.spinner("분석 중..."):
        analyses = analyze_all(raw_data)

    record = {
        "theme":    theme_name,
        "tickers":  tickers,
        "analyses": analyses,
        "time":     datetime.now().strftime("%H:%M"),
    }
    # Avoid duplicate entries for same theme
    st.session_state.history = [
        h for h in st.session_state.history if h["theme"] != theme_name
    ]
    st.session_state.history.append(record)
    st.session_state.current = record
    st.rerun()


# ── Display results ───────────────────────────────────────────────────────────
cur = st.session_state.current

if cur is None:
    st.info("테마를 선택하고 **분석 시작**을 눌러주세요.", icon="👆")
    st.stop()

theme_name = cur["theme"]
tickers    = cur["tickers"]
analyses   = cur["analyses"]

st.success(f"**{theme_name}** — {len(analyses)}개 기업 분석 완료", icon="✅")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_summary, tab_income, tab_cf, tab_price, tab_save = st.tabs([
    "📊 요약",
    "💰 수익성",
    "💵 현금흐름",
    "📈 주가",
    "💾 저장",
])

# ── Tab 1: Summary ────────────────────────────────────────────────────────────
with tab_summary:
    st.subheader(f"{theme_name} — 성장 요약")
    df = build_summary_df(analyses)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "순위":     st.column_config.NumberColumn(width="small"),
            "Ticker":  st.column_config.TextColumn(width="small"),
            "성장 패턴": st.column_config.TextColumn(width="medium"),
        },
    )

    # Valuation quick-look
    val_rows = [
        {
            "Ticker":  t,
            "회사명":   (a.get("name") or "")[:28],
            "P/E":     f"{a['pe_ratio']:.1f}x" if a.get("pe_ratio") else "N/A",
            "P/S":     f"{a['ps_ratio']:.1f}x" if a.get("ps_ratio") else "N/A",
            "시가총액":  f"${a['market_cap']/1e9:.1f}B" if a.get("market_cap") else "N/A",
        }
        for t, a in sorted(analyses.items(), key=lambda x: x[1].get("rank", 99))
    ]
    st.subheader("밸류에이션")
    st.dataframe(pd.DataFrame(val_rows), use_container_width=True, hide_index=True)

# ── Tab 2: Income / profitability ─────────────────────────────────────────────
with tab_income:
    st.subheader("수익성 대시보드")
    fig_income = build_figure(theme_name, analyses)
    fig_income.update_layout(height=1050)
    st.plotly_chart(fig_income, use_container_width=True)

# ── Tab 3: Cash flow ──────────────────────────────────────────────────────────
with tab_cf:
    st.subheader("현금흐름 대시보드")
    st.caption("FCF = 영업현금흐름 − 자본지출(CapEx)")
    fig_cf = build_cashflow_figure(theme_name, analyses)
    st.plotly_chart(fig_cf, use_container_width=True)

# ── Tab 4: Stock price ────────────────────────────────────────────────────────
with tab_price:
    st.subheader("주가 추이 (5년)")
    st.caption("정규화 차트: 모든 종목의 시작 시점을 100으로 맞춰 상대 수익률을 비교합니다.")
    fig_price = build_price_figure(theme_name, analyses)
    st.plotly_chart(fig_price, use_container_width=True)

# ── Tab 5: Save / download ────────────────────────────────────────────────────
with tab_save:
    st.subheader("분석 결과 저장")

    col_a, col_b, col_c = st.columns(3)

    # CSV
    csv_bytes = build_summary_df(analyses).to_csv(index=False).encode("utf-8-sig")
    col_a.download_button(
        label="⬇️ CSV 다운로드",
        data=csv_bytes,
        file_name=f"{theme_name.replace(' ','_')}_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Income HTML
    html_income = build_figure(theme_name, analyses).to_html(include_plotlyjs="cdn").encode("utf-8")
    col_b.download_button(
        label="⬇️ 수익성 차트 (HTML)",
        data=html_income,
        file_name=f"{theme_name.replace(' ','_')}_income.html",
        mime="text/html",
        use_container_width=True,
    )

    # Cash flow HTML
    html_cf = build_cashflow_figure(theme_name, analyses).to_html(include_plotlyjs="cdn").encode("utf-8")
    col_c.download_button(
        label="⬇️ 현금흐름 차트 (HTML)",
        data=html_cf,
        file_name=f"{theme_name.replace(' ','_')}_cashflow.html",
        mime="text/html",
        use_container_width=True,
    )

    # Price HTML
    html_price = build_price_figure(theme_name, analyses).to_html(include_plotlyjs="cdn").encode("utf-8")
    st.download_button(
        label="⬇️ 주가 차트 (HTML)",
        data=html_price,
        file_name=f"{theme_name.replace(' ','_')}_price.html",
        mime="text/html",
        use_container_width=True,
    )

    st.divider()
    st.caption(
        "💡 CSV는 엑셀에서 바로 열립니다. HTML 파일은 브라우저에서 인터랙티브 차트로 확인할 수 있습니다."
    )
