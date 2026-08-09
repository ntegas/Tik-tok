"""
Watchlist: список тикеров без сделок, без обязательной цены (см. границы
проекта — real-time/websocket и обязательные котировки вне MVP).
"""
import datetime
import sqlite3


def add(conn: sqlite3.Connection, ticker: str, list_name: str = "default", added_at: str | None = None) -> None:
    added_at = added_at or datetime.date.today().isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO watchlist (ticker, added_at, list_name) VALUES (?, ?, ?)",
        (ticker.upper(), added_at, list_name),
    )


def remove(conn: sqlite3.Connection, ticker: str, list_name: str = "default") -> None:
    conn.execute(
        "DELETE FROM watchlist WHERE ticker = ? AND list_name = ?",
        (ticker.upper(), list_name),
    )


def list_tickers(conn: sqlite3.Connection, list_name: str | None = None) -> list[sqlite3.Row]:
    if list_name is None:
        return conn.execute("SELECT * FROM watchlist ORDER BY list_name, added_at").fetchall()
    return conn.execute(
        "SELECT * FROM watchlist WHERE list_name = ? ORDER BY added_at", (list_name,)
    ).fetchall()
