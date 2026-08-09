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
