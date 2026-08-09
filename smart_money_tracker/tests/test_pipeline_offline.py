"""
Оффлайн-проверка шага 1: DB-слой и маппинг holdings-строк без обращения к
data.sec.gov (в этой песочнице сеть до SEC EDGAR заблокирована политикой
окружения — см. smart_money_tracker/README.md). Настоящий CUSIP->ticker
маппинг тестируется по-настоящему: используется offline-датасет, который
edgartools носит с собой в пакете (edgar/reference/data/ct.pq), а не мок.

Живой прогон (Company.get_filings(...) и реальный infotable) нужно делать
там, где data.sec.gov доступен — см. scripts/fetch_13f.py и README.
"""
import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db
from scripts.fetch_13f import holdings_df_to_rows


def make_fake_holdings_df() -> pd.DataFrame:
    """Форма как у ThirteenF.holdings (Type == 'Shares' для long equity), но
    вручную — реальные CUSIP Apple/Coca-Cola/Bank of America, чтобы проверить
    настоящую offline CUSIP->ticker таблицу edgartools, плюс один неизвестный
    CUSIP, чтобы проверить путь "ticker не резолвится"."""
    return pd.DataFrame(
        [
            {"Issuer": "APPLE INC", "Class": "COM", "Cusip": "037833100", "Ticker": "AAPL",
             "Type": "Shares", "PutCall": "", "SharesPrnAmount": 300000000, "Value": 68_000_000_000},
            {"Issuer": "COCA COLA CO", "Class": "COM", "Cusip": "191216100", "Ticker": "KO",
             "Type": "Shares", "PutCall": "", "SharesPrnAmount": 400000000, "Value": 28_000_000_000},
            {"Issuer": "BANK OF AMERICA CORP", "Class": "COM", "Cusip": "060505104", "Ticker": "BAC",
             "Type": "Shares", "PutCall": "", "SharesPrnAmount": 1000000000, "Value": 41_000_000_000},
            {"Issuer": "UNKNOWN OBSCURE CO", "Class": "COM", "Cusip": "999999999", "Ticker": None,
             "Type": "Shares", "PutCall": "", "SharesPrnAmount": 1000, "Value": 10000},
            {"Issuer": "APPLE INC", "Class": "CALL", "Cusip": "037833100", "Ticker": "AAPL",
             "Type": "Shares", "PutCall": "Call", "SharesPrnAmount": 5000, "Value": 100000},
        ]
    )


def resolve_real_cusip_tickers(df: pd.DataFrame) -> pd.DataFrame:
    """Прогоняет реальную offline CUSIP->Ticker таблицу edgartools поверх
    тестового датафрейма, как это делает настоящий infotable-парсер."""
    from edgar.reference.tickers import cusip_ticker_mapping

    mapping = cusip_ticker_mapping(allow_duplicate_cusips=False)
    df = df.copy()
    df["Ticker"] = df["Cusip"].map(mapping["Ticker"])
    return df


def test_cusip_ticker_mapping_resolves_known_names():
    df = resolve_real_cusip_tickers(make_fake_holdings_df())
    resolved = dict(zip(df["Cusip"], df["Ticker"]))
    assert resolved["037833100"] == "AAPL"
    assert resolved["191216100"] == "KO"
    assert resolved["060505104"] == "BAC"
    assert pd.isna(resolved["999999999"])  # заведомо не существующий CUSIP
    print("OK: offline CUSIP->ticker маппинг резолвит AAPL/KO/BAC и не выдумывает тикер для мусора")


def test_holdings_df_to_rows_filters_options_and_maps_columns():
    df = resolve_real_cusip_tickers(make_fake_holdings_df())
    rows = holdings_df_to_rows(df)

    # Опцион (PutCall='Call') должен быть отфильтрован — вне MVP-скоупа
    assert len(rows) == 4
    assert all(r["cusip"] != "037833100" or r["ticker"] == "AAPL" for r in rows)

    by_cusip = {r["cusip"]: r for r in rows}
    assert by_cusip["037833100"]["shares"] == 300000000
    assert by_cusip["037833100"]["value"] == 68_000_000_000
    assert by_cusip["999999999"]["ticker"] is None  # честно NULL, не выдуманное значение
    print("OK: holdings_df_to_rows фильтрует опционы и корректно маппит колонки")


def test_db_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db.DB_PATH = os.path.join(tmp, "test.db")
        db.init_db()
        conn = db.get_connection()

        investor_id = db.upsert_investor(conn, "Test Investor", "Test Fund LLC", "0000000001")
        filing_id = db.insert_filing(
            conn, investor_id, "0000000001-24-000001", "13F-HR",
            "2024-06-30", "2024-08-14", is_amendment=False, amendment_of=None,
        )

        df = resolve_real_cusip_tickers(make_fake_holdings_df())
        rows = holdings_df_to_rows(df)
        db.replace_holdings(conn, filing_id, rows)
        conn.commit()

        stored = conn.execute("SELECT cusip, ticker, shares, value FROM holdings WHERE filing_id = ?", (filing_id,)).fetchall()
        assert len(stored) == 4
        aapl = next(r for r in stored if r["cusip"] == "037833100")
        assert aapl["ticker"] == "AAPL"
        assert aapl["shares"] == 300000000

        # re-run fetch для того же filing не должен дублировать holdings
        db.replace_holdings(conn, filing_id, rows)
        conn.commit()
        stored_again = conn.execute("SELECT COUNT(*) AS c FROM holdings WHERE filing_id = ?", (filing_id,)).fetchone()
        assert stored_again["c"] == 4

        conn.close()
        print("OK: investors/filings/holdings пишутся и переиспользуются идемпотентно")


if __name__ == "__main__":
    test_cusip_ticker_mapping_resolves_known_names()
    test_holdings_df_to_rows_filters_options_and_maps_columns()
    test_db_roundtrip()
    print("\nВсе оффлайн-проверки прошли.")
