"""
Шаг 2 roadmap: сравнение кварталов, статус по каждой позиции —
NEW / ADD / REDUCE / EXIT / HOLD, с % изменения shares.

Логика намеренно простая (без скоринга, без порогов "значимости" — только
факт и сырой процент, см. границы проекта): сравниваем shares текущего
filing с прошлым по CUSIP.
"""
import sqlite3

import db


def _status_for_change(prev_shares: int, curr_shares: int) -> tuple[str, float]:
    if curr_shares > prev_shares:
        status = "ADD"
    elif curr_shares < prev_shares:
        status = "REDUCE"
    else:
        status = "HOLD"
    pct_change = 0.0 if prev_shares == 0 else (curr_shares - prev_shares) / prev_shares * 100
    return status, pct_change


def compare_filing_pair(conn: sqlite3.Connection, prev_filing_id: int, curr_filing_id: int) -> dict:
    """Проставляет status/pct_change на holdings текущего filing и добавляет
    EXIT-заглушки для позиций, которые были в прошлом квартале и пропали.
    Идемпотентно: безопасно перезапускать для одной и той же пары filings."""
    db.clear_synthetic_exits(conn, curr_filing_id)

    # EXIT rows on prev are placeholders from an earlier transition, not real
    # holdings — excluding them stops a position from being re-flagged EXIT
    # every subsequent quarter after it actually left the portfolio.
    prev_holdings = {h["cusip"]: h for h in db.get_holdings(conn, prev_filing_id) if h["status"] != "EXIT"}
    curr_holdings = {h["cusip"]: h for h in db.get_holdings(conn, curr_filing_id)}

    counts = {"NEW": 0, "ADD": 0, "REDUCE": 0, "HOLD": 0, "EXIT": 0}

    for cusip, curr in curr_holdings.items():
        prev = prev_holdings.get(cusip)
        if prev is None:
            status, pct_change = "NEW", None
        else:
            status, pct_change = _status_for_change(prev["shares"], curr["shares"])
        db.set_holding_status(conn, curr["id"], status, pct_change)
        counts[status] += 1

    for cusip, prev in prev_holdings.items():
        if cusip not in curr_holdings:
            db.insert_exit_holding(conn, curr_filing_id, cusip, prev["ticker"], prev["issuer"])
            counts["EXIT"] += 1

    return counts


def compare_investor_history(conn: sqlite3.Connection, investor_id: int) -> list[dict]:
    """Сравнивает все последовательные пары filings инвестора (по periods,
    amendments схлопнуты через get_effective_filings). Возвращает по одной
    записи на переход период->период с итогами по статусам."""
    filings = db.get_effective_filings(conn, investor_id)
    results = []
    for prev_filing, curr_filing in zip(filings, filings[1:]):
        counts = compare_filing_pair(conn, prev_filing["id"], curr_filing["id"])
        results.append(
            {
                "from_period": prev_filing["period"],
                "to_period": curr_filing["period"],
                "counts": counts,
            }
        )
    return results
