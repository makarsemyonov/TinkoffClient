from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

df = cli.portfolio.get_positions("Облигации")

print(df)