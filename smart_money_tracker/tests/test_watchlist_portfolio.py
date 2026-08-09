"""
Оффлайн-проверка шага 3: watchlist и portfolio. Чистая работа с БД, сеть не
нужна (у portfolio ещё и в принципе нет ничего сетевого — цены не подключены).
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
import portfolio
import watchlist


def fresh_conn(tmp):
    db.DB_PATH = os.path.join(tmp, "test.db")
    db.init_db()
    return db.get_connection()


def test_watchlist_add_remove_dedup_and_multiple_lists():
    with tempfile.TemporaryDirectory() as tmp:
        conn = fresh_conn(tmp)

        watchlist.add(conn, "googl", added_at="2024-01-01")
        watchlist.add(conn, "GOOGL", added_at="2024-01-02")  # тот же тикер, регистр не важен -> не дублируется
        watchlist.add(conn, "aapl", list_name="tech", added_at="2024-01-01")
        conn.commit()

        default_list = watchlist.list_tickers(conn, "default")
        assert len(default_list) == 1
        assert default_list[0]["ticker"] == "GOOGL"
        assert default_list[0]["added_at"] == "2024-01-01"  # первая запись не перезаписана

        tech_list = watchlist.list_tickers(conn, "tech")
        assert len(tech_list) == 1 and tech_list[0]["ticker"] == "AAPL"

        watchlist.remove(conn, "googl")  # регистр не важен и на удалении
        conn.commit()
        assert watchlist.list_tickers(conn, "default") == []
        assert len(watchlist.list_tickers(conn, "tech")) == 1  # другой список не затронут

        conn.close()
        print("OK: watchlist — дедуп по (ticker, list), регистронезависимость, списки не пересекаются")


def test_portfolio_average_cost_across_buys_and_partial_sell():
    with tempfile.TemporaryDirectory() as tmp:
        conn = fresh_conn(tmp)

        portfolio.add_transaction(conn, "GOOGL", "buy", 10, 100.0, "2024-01-01")
        portfolio.add_transaction(conn, "GOOGL", "buy", 10, 200.0, "2024-02-01")
        # avg cost после двух покупок: (10*100 + 10*200) / 20 = 150
        portfolio.add_transaction(conn, "GOOGL", "sell", 5, 999.0, "2024-03-01")
        # продажа не меняет avg cost оставшейся позиции (weighted average), только shares/invested
        conn.commit()

        positions = portfolio.compute_positions(conn)
        assert len(positions) == 1
        p = positions[0]
        assert p["ticker"] == "GOOGL"
        assert p["shares_held"] == 15
        assert p["avg_cost"] == 150.0
        assert p["invested"] == 15 * 150.0

        conn.close()
        print("OK: portfolio — weighted average cost корректен после buy/buy/sell")


def test_portfolio_fully_closed_position_not_shown():
    with tempfile.TemporaryDirectory() as tmp:
        conn = fresh_conn(tmp)
        portfolio.add_transaction(conn, "AAPL", "buy", 5, 100.0, "2024-01-01")
        portfolio.add_transaction(conn, "AAPL", "sell", 5, 120.0, "2024-02-01")
        conn.commit()

        assert portfolio.compute_positions(conn) == []
        conn.close()
        print("OK: полностью закрытая позиция не показывается как открытая")


def test_portfolio_overselling_raises_clear_error():
    with tempfile.TemporaryDirectory() as tmp:
        conn = fresh_conn(tmp)
        portfolio.add_transaction(conn, "AAPL", "buy", 5, 100.0, "2024-01-01")
        portfolio.add_transaction(conn, "AAPL", "sell", 999, 100.0, "2024-02-01")
        conn.commit()

        try:
            portfolio.compute_positions(conn)
            assert False, "должно было упасть на продаже больше, чем есть"
        except ValueError as e:
            assert "AAPL" in str(e)

        conn.close()
        print("OK: продажа сверх позиции честно падает с понятной ошибкой, а не уходит в минус молча")


if __name__ == "__main__":
    test_watchlist_add_remove_dedup_and_multiple_lists()
    test_portfolio_average_cost_across_buys_and_partial_sell()
    test_portfolio_fully_closed_position_not_shown()
    test_portfolio_overselling_raises_clear_error()
    print("\nВсе оффлайн-проверки watchlist/portfolio прошли.")
