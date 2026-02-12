from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")
df = cli.account.get_accounts()
print(df)