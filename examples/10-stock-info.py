from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

print(cli.market.stock_info("SBER"))