"""
US Stock Theme Analyzer
Usage:
  python main.py                        # interactive prompt
  python main.py ai                     # analyze AI theme
  python main.py semiconductor --top 5  # top 5 tickers only
  python main.py --tickers AAPL MSFT GOOGL --name "My Picks"
"""

import argparse
import sys
import webbrowser
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from themes import find_theme, list_themes
from fetcher import fetch_theme_data
from analyzer import analyze_all
from charts import create_dashboard

console = Console()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="US Stock Theme Analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("theme", nargs="?", help="Theme key or name (e.g. ai, semiconductor, ev)")
    p.add_argument("--tickers", nargs="+", metavar="TICKER", help="Custom ticker list")
    p.add_argument("--name", default=None, help="Custom theme name (used with --tickers)")
    p.add_argument("--top", type=int, default=None, help="Limit to top N tickers per theme")
    p.add_argument("--output", default=None, help="Output HTML path (default: <theme>_report.html)")
    p.add_argument("--no-browser", action="store_true", help="Do not open browser after saving")
    return p.parse_args()


def resolve_theme(args: argparse.Namespace):
    """Return (theme_name, tickers) from args or interactive prompt."""
    if args.tickers:
        name = args.name or "Custom"
        return name, args.tickers

    query = args.theme
    if not query:
        console.print("\n[bold]사용 가능한 테마:[/bold]")
        list_themes(console)
        query = Prompt.ask("\n분석할 테마를 입력하세요").strip()

    theme = find_theme(query)
    if not theme:
        console.print(f"\n[red]테마 '{query}'를 찾지 못했습니다.[/red]")
        console.print("위 표의 Key 또는 Theme 이름으로 다시 시도하세요.")
        sys.exit(1)

    tickers = theme["tickers"]
    if args.top:
        tickers = tickers[: args.top]

    return theme["name"], tickers


def main() -> None:
    args = parse_args()
    theme_name, tickers = resolve_theme(args)

    console.print(f"\n[bold green]테마:[/bold green] {theme_name}")
    console.print(f"[bold green]종목:[/bold green] {', '.join(tickers)}\n")

    # 1. Fetch
    raw_data = fetch_theme_data(tickers, console)
    if not raw_data:
        console.print("[red]데이터를 가져올 수 없습니다. 종목 코드를 확인해 주세요.[/red]")
        sys.exit(1)

    # 2. Analyze
    analyses = analyze_all(raw_data)

    # 3. Output
    safe_name = theme_name.replace(" ", "_").replace("/", "-").lower()
    output_path = args.output or f"{safe_name}_report.html"
    create_dashboard(theme_name, analyses, output_path, console)

    abs_path = Path(output_path).resolve()
    console.print(f"\n[bold green]✓ 리포트 저장 완료:[/bold green] {abs_path}")

    if not args.no_browser:
        webbrowser.open(abs_path.as_uri())


if __name__ == "__main__":
    main()
