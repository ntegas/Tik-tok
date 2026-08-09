"""
Шаг 1 roadmap: настроить EdgarTools, вытащить последний 13F-HR для нескольких
инвесторов из investors.py и убедиться, что парсинг holdings и CUSIP->ticker
маппинг работают.

Использование:
    python3 scripts/fetch_13f.py

Требует EDGAR_IDENTITY в .env (см. .env.example) — SEC EDGAR отклоняет запросы
без identity вида "Имя email@example.com".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
import db
from investors import INVESTORS


def holdings_df_to_rows(holdings_df) -> list[dict]:
    """Long-equity holdings (Type == 'Shares', без опционов) -> строки для БД.

    Вынесено отдельно от fetch_investor, чтобы тестировать маппинг колонок
    и CUSIP->ticker резолюцию без обращения к сети (см. tests/).
    """
    equity = holdings_df[holdings_df["Type"] == "Shares"]
    if "PutCall" in equity.columns:
        equity = equity[equity["PutCall"].isin(["", None]) | equity["PutCall"].isna()]

    return [
        {
            "cusip": row["Cusip"],
            "ticker": row["Ticker"] if row["Ticker"] and str(row["Ticker"]) != "nan" else None,
            "issuer": row["Issuer"],
            "shares": int(row["SharesPrnAmount"]),
            "value": int(row["Value"]),
            "status": None,
            "pct_change": None,
        }
        for _, row in equity.iterrows()
    ]


def fetch_investor(conn, edgar_company_cls, investor: dict) -> None:
    from edgar.thirteenf.models import ThirteenF

    investor_id = db.upsert_investor(conn, investor["name"], investor["fund"], investor["cik"])

    company = edgar_company_cls(investor["cik"])
    filings = company.get_filings(form=["13F-HR", "13F-HR/A"])
    if len(filings) == 0:
        print(f"  ! {investor['name']}: нет 13F-HR filings для CIK {investor['cik']}")
        return

    filing = filings.latest()
    tf = ThirteenF(filing, use_latest_period_of_report=True)

    if not tf.has_infotable():
        print(f"  ! {investor['name']}: последний filing без information table ({filing.accession_no})")
        return

    holdings_df = tf.holdings
    if holdings_df is None or len(holdings_df) == 0:
        print(f"  ! {investor['name']}: information table пустая ({filing.accession_no})")
        return

    filing_id = db.insert_filing(
        conn,
        investor_id=investor_id,
        accession_no=filing.accession_no,
        form_type=filing.form,
        period=tf.report_period,
        filed_date=tf.filing_date,
        is_amendment=tf.is_amendment,
        amendment_of=None,  # резолвится на шаге 2 (сравнение кварталов)
    )

    holdings = holdings_df_to_rows(holdings_df)
    db.replace_holdings(conn, filing_id, holdings)
    conn.commit()

    resolved = sum(1 for h in holdings if h["ticker"])
    print(
        f"  ok {investor['name']} ({investor['fund']}): {filing.accession_no}, "
        f"период {tf.report_period}, {len(holdings)} holdings, "
        f"{resolved}/{len(holdings)} с тикером"
    )


def main() -> None:
    if not config.EDGAR_IDENTITY:
        print("EDGAR_IDENTITY не задан в .env — SEC EDGAR отклонит запросы без него.")
        print('Пример: EDGAR_IDENTITY="Alexis alexis@example.com"')
        sys.exit(1)

    from edgar import Company, set_identity

    set_identity(config.EDGAR_IDENTITY)

    db.init_db()
    conn = db.get_connection()

    print(f"Загружаю последние 13F-HR для {len(INVESTORS)} инвесторов...")
    for investor in INVESTORS:
        try:
            fetch_investor(conn, Company, investor)
        except Exception as e:
            print(f"  ! {investor['name']}: ошибка — {e}")

    conn.close()


if __name__ == "__main__":
    main()
