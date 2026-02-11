from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

df = cli.get_positions("Облигации")

print(df)