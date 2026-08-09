"""
Шаг 5 roadmap: минимальный UI поверх того, что уже есть. По спеке
полноценный веб-фронт не обязателен для личного использования — это
read-only дашборд первой итерации, без форм добавления/редактирования.
Добавить тикер в watchlist или записать сделку — по-прежнему через
scripts/watchlist_cli.py и scripts/portfolio_cli.py.

Запуск:
    streamlit run app.py
"""
import streamlit as st

import db
import overlap
import portfolio
import watchlist

st.set_page_config(page_title="Smart Money Tracker", layout="wide")


@st.cache_resource
def get_conn():
    db.init_db()
    return db.get_connection()


def render_overlap(conn):
    st.header("Overlap")
    st.caption(
        "Тикеры из watchlist/portfolio, которые держат отслеживаемые "
        "инвесторы по своему последнему 13F. Только факты, без скоринга."
    )
    entries = overlap.compute_overlap(conn)
    if not entries:
        st.info(
            "Пересечений нет: либо watchlist/portfolio пусты, либо ни один "
            "отслеживаемый инвестор не держит эти тикеры по последнему 13F."
        )
        return
    for entry in entries:
        with st.expander(overlap.format_overlap_line(entry), expanded=True):
            rows = [
                {
                    "Инвестор": h["investor"],
                    "Фонд": h["fund"],
                    "Статус": h["status"] or "?",
                    "% изменения": f"{h['pct_change']:+.1f}%" if h["pct_change"] is not None else "—",
                    "Период": h["period"],
                }
                for h in entry["holders"]
            ]
            st.table(rows)


def render_watchlist(conn):
    st.header("Watchlist")
    rows = watchlist.list_tickers(conn)
    if not rows:
        st.info("Watchlist пуст. Добавить: python3 scripts/watchlist_cli.py add <TICKER>")
        return
    st.table(
        [{"Тикер": r["ticker"], "Список": r["list_name"], "Добавлен": r["added_at"]} for r in rows]
    )


def render_portfolio(conn):
    st.header("Portfolio")
    try:
        positions = portfolio.compute_positions(conn)
    except ValueError as e:
        st.error(f"Ошибка в данных сделок: {e}")
        return
    if not positions:
        st.info("Открытых позиций нет. Записать сделку: python3 scripts/portfolio_cli.py buy <TICKER> ...")
        return
    st.table(
        [
            {
                "Тикер": p["ticker"],
                "Shares": p["shares_held"],
                "Avg cost": p["avg_cost"],
                "Invested": p["invested"],
            }
            for p in positions
        ]
    )
    st.caption(
        "Unrealized P/L и return % пока не считаются — источник цен "
        "(Alpha Vantage / yfinance) ещё не выбран, см. README."
    )


def render_investors(conn):
    st.header("Инвесторы")
    investors = conn.execute("SELECT * FROM investors ORDER BY name").fetchall()
    if not investors:
        st.info("Инвесторы ещё не загружены: python3 scripts/fetch_13f.py")
        return
    for inv in investors:
        filings = db.get_effective_filings(conn, inv["id"])
        if not filings:
            st.subheader(f"{inv['name']} ({inv['fund']})")
            st.caption("Filings не загружены")
            continue
        latest = filings[-1]
        holdings = [h for h in db.get_holdings(conn, latest["id"]) if h["status"] != "EXIT" and h["shares"] > 0]
        with st.expander(f"{inv['name']} ({inv['fund']}) — период {latest['period']}, {len(holdings)} holdings"):
            st.table(
                [
                    {
                        "Тикер": h["ticker"] or "—",
                        "Issuer": h["issuer"],
                        "Shares": h["shares"],
                        "Value": h["value"],
                        "Статус": h["status"] or "?",
                    }
                    for h in sorted(holdings, key=lambda h: h["value"], reverse=True)
                ]
            )


def main():
    st.title("Smart Money Tracker")
    conn = get_conn()

    tab_overlap, tab_watchlist, tab_portfolio, tab_investors = st.tabs(
        ["Overlap", "Watchlist", "Portfolio", "Инвесторы"]
    )
    with tab_overlap:
        render_overlap(conn)
    with tab_watchlist:
        render_watchlist(conn)
    with tab_portfolio:
        render_portfolio(conn)
    with tab_investors:
        render_investors(conn)


if __name__ == "__main__":
    main()
