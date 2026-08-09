"""
Шаг 3b roadmap: CLI для portfolio — ручной ввод сделок, average cost, invested.

unrealized P/L и return % не считаются: источник цен ещё не подключён
(см. смарт-money README, открытый вопрос Alpha Vantage vs yfinance).

Использование:
    python3 scripts/portfolio_cli.py buy GOOGL --shares 10 --price 150.5 --date 2024-06-01
    python3 scripts/portfolio_cli.py sell GOOGL --shares 4 --price 175.0 --date 2024-08-01
    python3 scripts/portfolio_cli.py positions
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
import portfolio


def main() -> None:
    parser = argparse.ArgumentParser(description="Portfolio CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    for side in ("buy", "sell"):
        p = sub.add_parser(side)
        p.add_argument("ticker")
        p.add_argument("--shares", type=float, required=True)
        p.add_argument("--price", type=float, required=True)
        p.add_argument("--date", required=True, help="YYYY-MM-DD")

    sub.add_parser("positions")

    args = parser.parse_args()

    db.init_db()
    conn = db.get_connection()

    if args.command in ("buy", "sell"):
        try:
            portfolio.add_transaction(conn, args.ticker, args.command, args.shares, args.price, args.date)
        except ValueError as e:
            print(f"! {e}")
            sys.exit(1)
        conn.commit()
        print(f"Записано: {args.command} {args.shares} {args.ticker.upper()} по {args.price} ({args.date})")
    elif args.command == "positions":
        try:
            positions = portfolio.compute_positions(conn)
        except ValueError as e:
            print(f"! {e}")
            sys.exit(1)
        if not positions:
            print("Открытых позиций нет")
        for p in positions:
            print(
                f"  {p['ticker']}: {p['shares_held']} shares, "
                f"avg cost {p['avg_cost']}, invested {p['invested']}"
            )

    conn.close()


if __name__ == "__main__":
    main()
