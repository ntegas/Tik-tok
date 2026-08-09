"""
Шаг 4 roadmap: overlap-экран — главная уникальная функция проекта.

Какие тикеры из watchlist/portfolio держат/наращивают отслеживаемые
инвесторы. Только факты (кто держит, NEW/ADD/REDUCE/HOLD, сырой %) — без
скоринга, без "conviction score", см. границы проекта.
"""
import sqlite3

import db
import portfolio


def get_tracked_tickers(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """Тикеры из watchlist и открытых позиций portfolio, с пометкой источника
    (тикер может быть в обоих сразу)."""
    watchlist_tickers = {r["ticker"] for r in conn.execute("SELECT DISTINCT ticker FROM watchlist")}
    portfolio_tickers = {p["ticker"] for p in portfolio.compute_positions(conn)}
    return {"watchlist": watchlist_tickers, "portfolio": portfolio_tickers}


def compute_overlap(conn: sqlite3.Connection) -> list[dict]:
    """Для каждого отслеживаемого тикера — список инвесторов, которые держат
    его по последнему доступному 13F (эффективный filing на инвестора, см.
    get_effective_filings). Инвесторы, вышедшие из позиции (status='EXIT'
    или shares=0), не считаются держателями."""
    sources = get_tracked_tickers(conn)
    tracked = sources["watchlist"] | sources["portfolio"]
    if not tracked:
        return []

    investors = conn.execute("SELECT * FROM investors").fetchall()
    holders_by_ticker: dict[str, list[dict]] = {t: [] for t in tracked}

    for investor in investors:
        filings = db.get_effective_filings(conn, investor["id"])
        if not filings:
            continue
        latest_filing = filings[-1]
        for h in db.get_holdings(conn, latest_filing["id"]):
            if h["status"] == "EXIT" or h["shares"] == 0:
                continue
            if h["ticker"] not in holders_by_ticker:
                continue
            holders_by_ticker[h["ticker"]].append(
                {
                    "investor": investor["name"],
                    "fund": investor["fund"],
                    "status": h["status"],  # None, если compare_quarters ещё не запускался
                    "pct_change": h["pct_change"],
                    "period": latest_filing["period"],
                }
            )

    results = []
    for ticker in sorted(tracked):
        holders = holders_by_ticker[ticker]
        if not holders:
            continue  # ни один отслеживаемый инвестор не держит — не показываем пустые строки
        results.append(
            {
                "ticker": ticker,
                "in_watchlist": ticker in sources["watchlist"],
                "in_portfolio": ticker in sources["portfolio"],
                "holders": holders,
            }
        )
    return results


def format_overlap_line(entry: dict) -> str:
    where = []
    if entry["in_watchlist"]:
        where.append("watchlist")
    if entry["in_portfolio"]:
        where.append("portfolio")
    where_str = " + ".join(where)

    holders = entry["holders"]
    increasing = [h for h in holders if h["status"] in ("NEW", "ADD")]

    if increasing:
        return (
            f"{entry['ticker']} — в {where_str}, {len(increasing)} из {len(holders)} "
            f"инвесторов наращивают/открывают позицию в последнем 13F"
        )
    return (
        f"{entry['ticker']} — в {where_str}, {len(holders)} инвесторов держат позицию "
        f"в последнем 13F (без наращивания в этом периоде)"
    )
