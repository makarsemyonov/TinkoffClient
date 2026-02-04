from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

account = 'Algo-Trade'
ticker = 'SBER'

buy_id = cli.buy(account, ticker, 1, 306) # Лимитный ордер на покупку
print(cli.get_order_state(account, buy_id))

sell_id = cli.sell(account, ticker, 1) # Рыночный ордер на продажу
print(cli.get_order_state(account, sell_id))