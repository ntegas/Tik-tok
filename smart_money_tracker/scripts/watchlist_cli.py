"""
Шаг 3a roadmap: CLI для watchlist — без сделок, без обязательной цены.

Использование:
    python3 scripts/watchlist_cli.py add GOOGL
    python3 scripts/watchlist_cli.py add GOOGL --list crypto-adjacent
    python3 scripts/watchlist_cli.py remove GOOGL
    python3 scripts/watchlist_cli.py list
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
import watchlist


def main() -> None:
    parser = argparse.ArgumentParser(description="Watchlist CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add")
    add.add_argument("ticker")
    add.add_argument("--list", dest="list_name", default="default")

    remove = sub.add_parser("remove")
    remove.add_argument("ticker")
    remove.add_argument("--list", dest="list_name", default="default")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--list", dest="list_name", default=None)

    args = parser.parse_args()

    db.init_db()
    conn = db.get_connection()

    if args.command == "add":
        watchlist.add(conn, args.ticker, args.list_name)
        conn.commit()
        print(f"Добавлено: {args.ticker.upper()} ({args.list_name})")
    elif args.command == "remove":
        watchlist.remove(conn, args.ticker, args.list_name)
        conn.commit()
        print(f"Удалено: {args.ticker.upper()} ({args.list_name})")
    elif args.command == "list":
        rows = watchlist.list_tickers(conn, args.list_name)
        if not rows:
            print("Watchlist пуст")
        for r in rows:
            print(f"  {r['ticker']} ({r['list_name']}), добавлен {r['added_at']}")

    conn.close()


if __name__ == "__main__":
    main()
