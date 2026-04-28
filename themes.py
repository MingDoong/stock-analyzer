"""Theme-to-ticker mapping for US stock analysis."""

from difflib import get_close_matches
from typing import Optional, Dict
from rich.console import Console
from rich.table import Table

THEMES: Dict[str, Dict] = {
    "ai": {
        "name": "Artificial Intelligence",
        "aliases": ["artificial intelligence", "machine learning", "llm", "generative ai", "gen ai"],
        "tickers": ["NVDA", "MSFT", "GOOGL", "META", "AMZN", "PLTR", "AMD", "SMCI", "IBM", "AI"],
    },
    "semiconductor": {
        "name": "Semiconductors",
        "aliases": ["chips", "chip", "semi", "semis", "반도체"],
        "tickers": ["NVDA", "TSM", "INTC", "AMD", "QCOM", "AVGO", "MU", "AMAT", "LRCX", "KLAC"],
    },
    "ev": {
        "name": "Electric Vehicles",
        "aliases": ["electric vehicle", "electric car", "battery car", "전기차", "electric vehicles"],
        "tickers": ["TSLA", "RIVN", "LCID", "NIO", "LI", "XPEV", "F", "GM", "STLA", "PSNY"],
    },
    "cloud": {
        "name": "Cloud Computing",
        "aliases": ["cloud", "saas", "software as a service", "cloud computing"],
        "tickers": ["AMZN", "MSFT", "GOOGL", "CRM", "NOW", "SNOW", "DDOG", "NET", "ZS", "MDB"],
    },
    "cybersecurity": {
        "name": "Cybersecurity",
        "aliases": ["security", "cyber", "network security", "보안"],
        "tickers": ["CRWD", "PANW", "ZS", "FTNT", "OKTA", "S", "CYBR", "QLYS", "NET", "RPD"],
    },
    "biotech": {
        "name": "Biotechnology",
        "aliases": ["biotech", "biopharma", "pharmaceutical", "pharma", "healthcare", "바이오"],
        "tickers": ["MRNA", "BNTX", "REGN", "VRTX", "BIIB", "GILD", "AMGN", "ILMN", "EXAS", "RARE"],
    },
    "renewable": {
        "name": "Renewable Energy",
        "aliases": ["clean energy", "solar", "wind energy", "green energy", "cleantech", "신재생에너지"],
        "tickers": ["ENPH", "SEDG", "FSLR", "NEE", "BEP", "PLUG", "BE", "NOVA", "ARRY", "RUN"],
    },
    "fintech": {
        "name": "Financial Technology",
        "aliases": ["financial technology", "payments", "digital payments", "핀테크"],
        "tickers": ["SQ", "PYPL", "AFRM", "SOFI", "UPST", "V", "MA", "COIN", "HOOD", "NU"],
    },
    "ecommerce": {
        "name": "E-Commerce",
        "aliases": ["ecommerce", "e-commerce", "online retail", "online shopping", "이커머스"],
        "tickers": ["AMZN", "SHOP", "MELI", "SE", "ETSY", "W", "EBAY", "CPNG", "PDD", "BABA"],
    },
    "social": {
        "name": "Social Media",
        "aliases": ["social network", "social media", "소셜미디어"],
        "tickers": ["META", "SNAP", "PINS", "RDDT", "MTCH", "BMBL", "YY", "LNKD", "TWTR", "IAC"],
    },
    "gaming": {
        "name": "Gaming",
        "aliases": ["video games", "game", "esports", "게임"],
        "tickers": ["MSFT", "EA", "TTWO", "RBLX", "U", "DKNG", "NTES", "PLTK", "GLBE", "PGTS"],
    },
    "space": {
        "name": "Space & Aerospace",
        "aliases": ["aerospace", "space exploration", "defense", "우주"],
        "tickers": ["RKLB", "SPCE", "ASTS", "LMT", "RTX", "BA", "NOC", "GD", "KTOS", "AJRD"],
    },
    "streaming": {
        "name": "Streaming & Entertainment",
        "aliases": ["streaming", "entertainment", "media", "스트리밍"],
        "tickers": ["NFLX", "DIS", "PARA", "WBD", "ROKU", "SPOT", "AMZN", "AAPL", "FUBO", "LGF"],
    },
    "bigtech": {
        "name": "Big Tech (Magnificent 7)",
        "aliases": ["faang", "big tech", "mega cap", "magnificent seven", "mag7", "빅테크"],
        "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"],
    },
}


def find_theme(query: str) -> Optional[Dict]:
    """Find a theme by key, alias, or fuzzy match."""
    q = query.lower().strip()

    if q in THEMES:
        return THEMES[q]

    for key, theme in THEMES.items():
        aliases = [a.lower() for a in theme.get("aliases", [])]
        if q in aliases:
            return theme
        if any(q in alias or alias in q for alias in aliases):
            return theme

    name_to_key = {v["name"].lower(): k for k, v in THEMES.items()}
    close = get_close_matches(q, name_to_key.keys(), n=1, cutoff=0.45)
    if close:
        return THEMES[name_to_key[close[0]]]

    return None


def list_themes(console: Console) -> None:
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Key", style="bold cyan", width=14)
    table.add_column("Theme", width=28)
    table.add_column("Key Companies")

    for key, theme in THEMES.items():
        preview = ", ".join(theme["tickers"][:5])
        if len(theme["tickers"]) > 5:
            preview += " ..."
        table.add_row(key, theme["name"], preview)

    console.print(table)
