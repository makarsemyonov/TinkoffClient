from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

print(cli.market.get_current_price("SBER"))