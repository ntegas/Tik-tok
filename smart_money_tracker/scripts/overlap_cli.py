"""
Шаг 4 roadmap: overlap-экран. Ничего не тянет из сети — только читает то,
что уже загружено fetch_13f.py/compare_quarters.py и записано в watchlist/
portfolio.

Использование:
    python3 scripts/overlap_cli.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
import overlap


def main() -> None:
    db.init_db()
    conn = db.get_connection()

    entries = overlap.compute_overlap(conn)
    if not entries:
        print("Пересечений нет: либо watchlist/portfolio пусты, либо ни один")
        print("отслеживаемый инвестор не держит эти тикеры по последнему 13F.")
    for entry in entries:
        print(overlap.format_overlap_line(entry))
        for h in entry["holders"]:
            pct = f", {h['pct_change']:+.1f}%" if h["pct_change"] is not None else ""
            status = h["status"] or "?"
            print(f"    {h['investor']} ({h['fund']}): {status}{pct} — период {h['period']}")

    conn.close()


if __name__ == "__main__":
    main()
