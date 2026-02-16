from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

print(cli.market.convert_currency("USD", "RUB")) # Просто курс

print(cli.market.convert_currency("USD", "RUB", 10)) # Конвертация