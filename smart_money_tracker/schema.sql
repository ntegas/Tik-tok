-- Smart Money Tracker — SQLite schema.
-- Один пользователь, без multi-tenant. См. smart_money_tracker/README.md.

CREATE TABLE IF NOT EXISTS investors (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,          -- напр. "Warren Buffett"
    fund    TEXT NOT NULL,          -- напр. "Berkshire Hathaway Inc"
    cik     TEXT NOT NULL UNIQUE    -- SEC CIK, 10 цифр с ведущими нулями
);

CREATE TABLE IF NOT EXISTS filings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    investor_id     INTEGER NOT NULL REFERENCES investors(id),
    accession_no    TEXT NOT NULL UNIQUE,  -- уникальный номер filing в EDGAR
    form_type       TEXT NOT NULL,         -- '13F-HR' | '13F-HR/A'
    period          TEXT NOT NULL,         -- report period end date, YYYY-MM-DD
    filed_date      TEXT NOT NULL,         -- YYYY-MM-DD
    is_amendment    INTEGER NOT NULL DEFAULT 0,
    amendment_of    INTEGER REFERENCES filings(id),  -- ссылка на исходный filing, если amendment
    UNIQUE (investor_id, period, is_amendment, accession_no)
);

CREATE TABLE IF NOT EXISTS holdings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id   INTEGER NOT NULL REFERENCES filings(id),
    cusip       TEXT NOT NULL,
    ticker      TEXT,               -- NULL, если CUSIP не резолвится
    issuer      TEXT NOT NULL,
    shares      INTEGER NOT NULL,
    value       INTEGER NOT NULL,   -- в долларах (не тысячах)
    status      TEXT,               -- NEW | ADD | REDUCE | EXIT | HOLD, считается при сравнении кварталов
    pct_change  REAL                -- % изменения shares к прошлому кварталу, NULL для NEW
);

CREATE INDEX IF NOT EXISTS idx_holdings_filing_id ON holdings(filing_id);
CREATE INDEX IF NOT EXISTS idx_holdings_cusip ON holdings(cusip);
CREATE INDEX IF NOT EXISTS idx_filings_investor_id ON filings(investor_id);

CREATE TABLE IF NOT EXISTS watchlist (
    ticker      TEXT NOT NULL,
    added_at    TEXT NOT NULL,      -- YYYY-MM-DD
    list_name   TEXT NOT NULL DEFAULT 'default',
    PRIMARY KEY (ticker, list_name)
);

CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker  TEXT NOT NULL,
    side    TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    shares  REAL NOT NULL,
    price   REAL NOT NULL,
    date    TEXT NOT NULL           -- YYYY-MM-DD
);
