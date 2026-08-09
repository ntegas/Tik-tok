"""
Оффлайн-проверка шага 2 (сравнение кварталов). Полностью синтетические
данные, сеть не нужна — вся логика в compare.py работает только с БД.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import compare
import db


def setup_investor_with_filings(conn, periods_holdings: list[tuple[str, list[dict]]]) -> int:
    investor_id = db.upsert_investor(conn, "Test Investor", "Test Fund LLC", "0000000001")
    for i, (period, holdings) in enumerate(periods_holdings):
        filing_id = db.insert_filing(
            conn, investor_id, f"acc-{period}", "13F-HR", period,
            filed_date=period, is_amendment=False, amendment_of=None,
        )
        db.replace_holdings(conn, filing_id, holdings)
    return investor_id


def holding(cusip, ticker, issuer, shares, value=1000):
    return {"cusip": cusip, "ticker": ticker, "issuer": issuer, "shares": shares, "value": value, "status": None, "pct_change": None}


def test_new_add_reduce_hold_exit_single_transition():
    with tempfile.TemporaryDirectory() as tmp:
        db.DB_PATH = os.path.join(tmp, "test.db")
        db.init_db()
        conn = db.get_connection()

        q1 = [
            holding("AAA", "AAA", "Company A", 1000),   # will be REDUCEd
            holding("BBB", "BBB", "Company B", 500),    # will be HOLD (unchanged)
            holding("CCC", "CCC", "Company C", 200),    # will EXIT
        ]
        q2 = [
            holding("AAA", "AAA", "Company A", 600),    # 1000 -> 600 = REDUCE
            holding("BBB", "BBB", "Company B", 500),    # unchanged = HOLD
            holding("DDD", "DDD", "Company D", 300),    # brand new = NEW
        ]
        investor_id = setup_investor_with_filings(conn, [("2024-03-31", q1), ("2024-06-30", q2)])

        transitions = compare.compare_investor_history(conn, investor_id)
        conn.commit()

        assert len(transitions) == 1
        counts = transitions[0]["counts"]
        assert counts == {"NEW": 1, "ADD": 0, "REDUCE": 1, "HOLD": 1, "EXIT": 1}

        q2_filing_id = conn.execute(
            "SELECT id FROM filings WHERE period = '2024-06-30'"
        ).fetchone()["id"]
        rows = {r["cusip"]: r for r in db.get_holdings(conn, q2_filing_id)}

        assert rows["AAA"]["status"] == "REDUCE"
        assert round(rows["AAA"]["pct_change"], 1) == -40.0  # (600-1000)/1000*100

        assert rows["BBB"]["status"] == "HOLD"
        assert rows["BBB"]["pct_change"] == 0.0

        assert rows["DDD"]["status"] == "NEW"
        assert rows["DDD"]["pct_change"] is None

        # CCC exited: not in q2's fetched holdings, but a synthetic EXIT row
        # must have been added so the drop is visible without a separate table
        assert rows["CCC"]["status"] == "EXIT"
        assert rows["CCC"]["shares"] == 0
        assert rows["CCC"]["pct_change"] == -100.0

        conn.close()
        print("OK: одна транзакция даёт корректные NEW/REDUCE/HOLD/EXIT и % изменения")


def test_add_status_and_exit_does_not_repeat_next_quarter():
    with tempfile.TemporaryDirectory() as tmp:
        db.DB_PATH = os.path.join(tmp, "test.db")
        db.init_db()
        conn = db.get_connection()

        q1 = [holding("AAA", "AAA", "Company A", 100), holding("CCC", "CCC", "Company C", 200)]
        q2 = [holding("AAA", "AAA", "Company A", 150)]  # AAA added to, CCC exited
        q3 = [holding("AAA", "AAA", "Company A", 150)]  # unchanged; CCC should NOT re-appear as EXIT again
        investor_id = setup_investor_with_filings(
            conn, [("2024-03-31", q1), ("2024-06-30", q2), ("2024-09-30", q3)]
        )

        transitions = compare.compare_investor_history(conn, investor_id)
        conn.commit()

        assert transitions[0]["counts"] == {"NEW": 0, "ADD": 1, "REDUCE": 0, "HOLD": 0, "EXIT": 1}
        # q2 -> q3: AAA unchanged (HOLD). CCC already left in the prior transition,
        # so it must not be flagged EXIT a second time.
        assert transitions[1]["counts"] == {"NEW": 0, "ADD": 0, "REDUCE": 0, "HOLD": 1, "EXIT": 0}

        conn.close()
        print("OK: EXIT не повторяется в следующем квартале после ухода позиции")


def test_rerun_comparison_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        db.DB_PATH = os.path.join(tmp, "test.db")
        db.init_db()
        conn = db.get_connection()

        q1 = [holding("AAA", "AAA", "Company A", 100), holding("CCC", "CCC", "Company C", 200)]
        q2 = [holding("AAA", "AAA", "Company A", 150)]
        investor_id = setup_investor_with_filings(conn, [("2024-03-31", q1), ("2024-06-30", q2)])

        compare.compare_investor_history(conn, investor_id)
        conn.commit()
        compare.compare_investor_history(conn, investor_id)  # rerun on purpose
        conn.commit()

        q2_filing_id = conn.execute("SELECT id FROM filings WHERE period = '2024-06-30'").fetchone()["id"]
        rows = db.get_holdings(conn, q2_filing_id)
        exit_rows = [r for r in rows if r["status"] == "EXIT"]

        assert len(exit_rows) == 1  # not duplicated by the second run
        conn.close()
        print("OK: повторный запуск сравнения не дублирует EXIT-строки")


if __name__ == "__main__":
    test_new_add_reduce_hold_exit_single_transition()
    test_add_status_and_exit_does_not_repeat_next_quarter()
    test_rerun_comparison_is_idempotent()
    print("\nВсе оффлайн-проверки сравнения кварталов прошли.")
