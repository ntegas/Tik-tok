"""
Portfolio: ручной ввод сделок (buy/sell), считаем average cost, invested.

unrealized P/L и return % требуют текущей цены — источник цен (Alpha Vantage
или yfinance, см. спеку) ещё не выбран/подключён, поэтому здесь их нет.
compute_positions() отдаёт всё, что можно посчитать без цены; когда появится
цена — unrealized P/L = (price - avg_cost) * shares, return % = P/L / invested * 100.

Метод учёта себестоимости — weighted average (не FIFO/LIFO): проще и
достаточно для личного трекера, где сделок немного.
"""
import sqlite3


def add_transaction(conn: sqlite3.Connection, ticker: str, side: str, shares: float, price: float, date: str) -> None:
    if side not in ("buy", "sell"):
        raise ValueError(f"side должен быть 'buy' или 'sell', получено {side!r}")
    if shares <= 0 or price <= 0:
        raise ValueError("shares и price должны быть положительными")
    conn.execute(
        "INSERT INTO portfolio_transactions (ticker, side, shares, price, date) VALUES (?, ?, ?, ?, ?)",
        (ticker.upper(), side, shares, price, date),
    )


def compute_positions(conn: sqlite3.Connection) -> list[dict]:
    """Weighted-average cost по каждому тикеру, в хронологическом порядке
    транзакций (date, затем id как tie-break для сделок в один день)."""
    rows = conn.execute(
        "SELECT * FROM portfolio_transactions ORDER BY ticker, date, id"
    ).fetchall()

    positions: dict[str, dict] = {}
    for row in rows:
        ticker = row["ticker"]
        pos = positions.setdefault(ticker, {"shares_held": 0.0, "cost_basis": 0.0})

        if row["side"] == "buy":
            pos["shares_held"] += row["shares"]
            pos["cost_basis"] += row["shares"] * row["price"]
        else:  # sell
            if row["shares"] > pos["shares_held"] + 1e-9:
                raise ValueError(
                    f"{ticker}: продажа {row['shares']} на {row['date']} превышает "
                    f"имеющиеся {pos['shares_held']} shares — проверь сделки"
                )
            avg_cost = pos["cost_basis"] / pos["shares_held"] if pos["shares_held"] > 0 else 0.0
            pos["cost_basis"] -= row["shares"] * avg_cost
            pos["shares_held"] -= row["shares"]

    results = []
    for ticker, pos in positions.items():
        if pos["shares_held"] <= 1e-9:
            continue  # позиция полностью закрыта, не показываем как открытую
        avg_cost = pos["cost_basis"] / pos["shares_held"]
        results.append(
            {
                "ticker": ticker,
                "shares_held": round(pos["shares_held"], 6),
                "avg_cost": round(avg_cost, 4),
                "invested": round(pos["cost_basis"], 2),
            }
        )
    return sorted(results, key=lambda p: p["ticker"])
