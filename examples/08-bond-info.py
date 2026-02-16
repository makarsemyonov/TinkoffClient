from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

print(cli.market.bond_info("RU000A10AAQ4"))