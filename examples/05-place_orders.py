from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

account = 'Algo-Trade'
ticker = 'SBER'

buy_id = cli.trade.buy(account, ticker, 1, 306) # Лимитный ордер на покупку
print(cli.trade.get_order_state(account, buy_id))

sell_id = cli.trade.sell(account, ticker, 1) # Рыночный ордер на продажу
print(cli.trade.get_order_state(account, sell_id))