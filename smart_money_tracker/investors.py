"""
Список отслеживаемых инвесторов для валидации пайплайна (шаг 1 roadmap).

CIK взяты из offline-датасета, который поставляется вместе с edgartools
(edgar/reference/data/portfolio_managers.json) — сверены без обращения к сети,
т.к. это первый прогон. Финальный список 20-30 инвесторов для MVP собирается
отдельно, вручную, по интересующим Алексиса фондам.
"""

INVESTORS = [
    {"name": "Warren Buffett", "fund": "Berkshire Hathaway Inc", "cik": "0001067983"},
    {"name": "Bill Ackman", "fund": "Pershing Square Capital Management, L.P.", "cik": "0001336528"},
    {"name": "Jim Simons / Peter Brown", "fund": "Renaissance Technologies LLC", "cik": "0001037389"},
    {"name": "Steven A. Cohen", "fund": "Point72 Asset Management, L.P.", "cik": "0001603466"},
    {"name": "Ray Dalio (fund)", "fund": "Bridgewater Associates, LP", "cik": "0001350694"},
]
