"""
Оффлайн-проверка шага 4 (overlap-экран). Чистая работа с БД, сеть не нужна.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import compare
import db
import overlap
import portfolio
import watchlist


def fresh_conn(tmp):
    db.DB_PATH = os.path.join(tmp, "test.db")
    db.init_db()
    return db.get_connection()


def holding(cusip, ticker, issuer, shares, value=1000):
    return {"cusip": cusip, "ticker": ticker, "issuer": issuer, "shares": shares, "value": value, "status": None, "pct_change": None}


def seed_investor(conn, name, fund, cik, periods_holdings):
    investor_id = db.upsert_investor(conn, name, fund, cik)
    for period, holdings in periods_holdings:
        filing_id = db.insert_filing(
            conn, investor_id, f"acc-{cik}-{period}", "13F-HR", period,
            filed_date=period, is_amendment=False, amendment_of=None,
        )
        db.replace_holdings(conn, filing_id, holdings)
    return investor_id


def test_overlap_shows_tracked_tickers_with_status_and_skips_exited():
    with tempfile.TemporaryDirectory() as tmp:
        conn = fresh_conn(tmp)

        # Investor A: added to GOOGL, exited MSFT between q1 and q2
        inv_a = seed_investor(
            conn, "Investor A", "Fund A LLC", "0000000001",
            [
                ("2024-03-31", [holding("GOOGL_CUSIP", "GOOGL", "Alphabet", 100), holding("MSFT_CUSIP", "MSFT", "Microsoft", 50)]),
                ("2024-06-30", [holding("GOOGL_CUSIP", "GOOGL", "Alphabet", 200)]),  # MSFT dropped -> EXIT
            ],
        )
        # Investor B: holds GOOGL unchanged, doesn't track NVDA at all
        inv_b = seed_investor(
            conn, "Investor B", "Fund B LLC", "0000000002",
            [
                ("2024-03-31", [holding("GOOGL_CUSIP", "GOOGL", "Alphabet", 300)]),
                ("2024-06-30", [holding("GOOGL_CUSIP", "GOOGL", "Alphabet", 300)]),  # unchanged -> HOLD
            ],
        )
        compare.compare_investor_history(conn, inv_a)
        compare.compare_investor_history(conn, inv_b)

        watchlist.add(conn, "GOOGL", added_at="2024-01-01")
        watchlist.add(conn, "MSFT", added_at="2024-01-01")  # in watchlist, but no tracked investor holds it anymore
        watchlist.add(conn, "TSLA", added_at="2024-01-01")  # in watchlist, no investor ever held it
        conn.commit()

        entries = overlap.compute_overlap(conn)
        by_ticker = {e["ticker"]: e for e in entries}

        # MSFT and TSLA have no current holders among tracked investors -> not shown
        assert "MSFT" not in by_ticker
        assert "TSLA" not in by_ticker

        googl = by_ticker["GOOGL"]
        assert googl["in_watchlist"] is True
        assert googl["in_portfolio"] is False
        statuses = {h["investor"]: h["status"] for h in googl["holders"]}
        assert statuses == {"Investor A": "ADD", "Investor B": "HOLD"}

        line = overlap.format_overlap_line(googl)
        assert "GOOGL" in line and "1 из 2" in line  # только A наращивает (ADD), B держит без изменений

        conn.close()
        print("OK: overlap показывает только реально держащих тикер инвесторов, EXIT/непересечения отфильтрованы")


def test_overlap_combines_watchlist_and_portfolio_sources():
    with tempfile.TemporaryDirectory() as tmp:
        conn = fresh_conn(tmp)

        seed_investor(
            conn, "Investor A", "Fund A LLC", "0000000001",
            [("2024-06-30", [holding("AAPL_CUSIP", "AAPL", "Apple", 1000)])],
        )

        portfolio.add_transaction(conn, "AAPL", "buy", 10, 150.0, "2024-01-01")
        watchlist.add(conn, "AAPL", added_at="2024-01-01")
        conn.commit()

        entries = overlap.compute_overlap(conn)
        assert len(entries) == 1
        assert entries[0]["in_watchlist"] is True
        assert entries[0]["in_portfolio"] is True

        conn.close()
        print("OK: тикер, который в watchlist и в portfolio одновременно, помечен обоими источниками")


def test_overlap_empty_when_no_tracked_tickers():
    with tempfile.TemporaryDirectory() as tmp:
        conn = fresh_conn(tmp)
        seed_investor(
            conn, "Investor A", "Fund A LLC", "0000000001",
            [("2024-06-30", [holding("AAPL_CUSIP", "AAPL", "Apple", 1000)])],
        )
        conn.commit()
        assert overlap.compute_overlap(conn) == []
        conn.close()
        print("OK: пустой watchlist/portfolio -> пустой overlap, без ошибок")


if __name__ == "__main__":
    test_overlap_shows_tracked_tickers_with_status_and_skips_exited()
    test_overlap_combines_watchlist_and_portfolio_sources()
    test_overlap_empty_when_no_tracked_tickers()
    print("\nВсе оффлайн-проверки overlap-экрана прошли.")
