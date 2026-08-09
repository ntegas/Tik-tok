"""
Шаг 2 roadmap: пересчитать NEW/ADD/REDUCE/EXIT/HOLD для всех инвесторов из
investors.py по уже загруженным filings (см. scripts/fetch_13f.py — этот
скрипт данные не тянет, только сравнивает то, что уже есть в БД).

Использование:
    python3 scripts/compare_quarters.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import compare
import db
from investors import INVESTORS


def main() -> None:
    db.init_db()
    conn = db.get_connection()

    for investor in INVESTORS:
        row = conn.execute("SELECT id FROM investors WHERE cik = ?", (investor["cik"],)).fetchone()
        if row is None:
            print(f"  ! {investor['name']}: ещё не загружался, сначала scripts/fetch_13f.py")
            continue

        transitions = compare.compare_investor_history(conn, row["id"])
        conn.commit()

        if not transitions:
            print(f"  - {investor['name']}: меньше двух periods в БД, сравнивать не с чем")
            continue

        for t in transitions:
            c = t["counts"]
            print(
                f"  ok {investor['name']}: {t['from_period']} -> {t['to_period']} — "
                f"NEW {c['NEW']}, ADD {c['ADD']}, REDUCE {c['REDUCE']}, HOLD {c['HOLD']}, EXIT {c['EXIT']}"
            )

    conn.close()


if __name__ == "__main__":
    main()
