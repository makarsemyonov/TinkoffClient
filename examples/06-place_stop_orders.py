from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

account = 'Algo-Trade'
ticker = 'SBER'

buy_id = cli.trade.buy(account, ticker, 1, 306) # Лимитный ордер на покупку
print(cli.trade.get_order_state(account, buy_id))

sl_id = cli.trade.long_stop_loss(account, ticker, 300, 300, 1) # Стоп-лосс с ценой активации и исполнения 300
tp_id = cli.trade.long_take_profit(account, ticker, 310, 310, 1) # Тейк-профит с ценой активации и исполнения 310