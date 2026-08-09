import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "smart_money.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def upsert_investor(conn: sqlite3.Connection, name: str, fund: str, cik: str) -> int:
    conn.execute(
        """
        INSERT INTO investors (name, fund, cik) VALUES (?, ?, ?)
        ON CONFLICT(cik) DO UPDATE SET name = excluded.name, fund = excluded.fund
        """,
        (name, fund, cik),
    )
    row = conn.execute("SELECT id FROM investors WHERE cik = ?", (cik,)).fetchone()
    return row["id"]


def insert_filing(
    conn: sqlite3.Connection,
    investor_id: int,
    accession_no: str,
    form_type: str,
    period: str,
    filed_date: str,
    is_amendment: bool,
    amendment_of: int | None,
) -> int:
    existing = conn.execute(
        "SELECT id FROM filings WHERE accession_no = ?", (accession_no,)
    ).fetchone()
    if existing:
        return existing["id"]
    cur = conn.execute(
        """
        INSERT INTO filings (investor_id, accession_no, form_type, period, filed_date, is_amendment, amendment_of)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (investor_id, accession_no, form_type, period, filed_date, int(is_amendment), amendment_of),
    )
    return cur.lastrowid


def replace_holdings(conn: sqlite3.Connection, filing_id: int, holdings: list[dict]) -> None:
    """Overwrite all holdings for a filing (safe to re-run fetch for the same filing)."""
    conn.execute("DELETE FROM holdings WHERE filing_id = ?", (filing_id,))
    conn.executemany(
        """
        INSERT INTO holdings (filing_id, cusip, ticker, issuer, shares, value, status, pct_change)
        VALUES (:filing_id, :cusip, :ticker, :issuer, :shares, :value, :status, :pct_change)
        """,
        [{**h, "filing_id": filing_id} for h in holdings],
    )


def get_effective_filings(conn: sqlite3.Connection, investor_id: int) -> list[sqlite3.Row]:
    """One filing per report period: the latest by filed_date (so a 13F-HR/A
    amendment supersedes the original it corrects), ordered oldest -> newest
    period. This is what quarter-over-quarter comparison should walk, per the
    project's amendment caveat (see README)."""
    return conn.execute(
        """
        SELECT f.* FROM filings f
        INNER JOIN (
            SELECT period, MAX(filed_date) AS max_filed_date
            FROM filings WHERE investor_id = ?
            GROUP BY period
        ) latest ON f.period = latest.period AND f.filed_date = latest.max_filed_date
        WHERE f.investor_id = ?
        ORDER BY f.period ASC
        """,
        (investor_id, investor_id),
    ).fetchall()


def get_holdings(conn: sqlite3.Connection, filing_id: int) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM holdings WHERE filing_id = ?", (filing_id,)).fetchall()


def set_holding_status(conn: sqlite3.Connection, holding_id: int, status: str, pct_change: float | None) -> None:
    conn.execute(
        "UPDATE holdings SET status = ?, pct_change = ? WHERE id = ?",
        (status, pct_change, holding_id),
    )


def clear_synthetic_exits(conn: sqlite3.Connection, filing_id: int) -> None:
    """Remove EXIT placeholder rows from a previous comparison run, so
    re-running the comparison doesn't accumulate duplicates."""
    conn.execute("DELETE FROM holdings WHERE filing_id = ? AND status = 'EXIT'", (filing_id,))


def insert_exit_holding(conn: sqlite3.Connection, filing_id: int, cusip: str, ticker: str | None, issuer: str) -> None:
    """A position held last period but absent this period doesn't appear in
    the 13F at all (13F only reports current holdings) — insert a shares=0
    placeholder row on the *current* filing so EXIT is visible without a
    separate comparison table, per the holdings.status column in schema.sql."""
    conn.execute(
        """
        INSERT INTO holdings (filing_id, cusip, ticker, issuer, shares, value, status, pct_change)
        VALUES (?, ?, ?, ?, 0, 0, 'EXIT', -100.0)
        """,
        (filing_id, cusip, ticker, issuer),
    )
