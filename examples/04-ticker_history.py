from datetime import datetime
from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")
date_from = datetime(2025, 11, 1)
date_to = datetime(2026, 2, 1)
ticker = "SBER"

df = cli.market.get_history(ticker, date_from, date_to)
print(df)