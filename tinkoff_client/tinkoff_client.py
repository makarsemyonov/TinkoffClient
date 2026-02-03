import pandas as pd
from pathlib import Path
from tinkoff.invest import Client
from tinkoff.invest import InstrumentStatus
from tinkoff.invest import OrderDirection, OrderType
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation
from tinkoff.invest import StopOrderDirection, StopOrderExpirationType, StopOrderType
from decimal import Decimal

class TinkoffClient:
  def __init__(self, token_file: str):
    path = Path(token_file)
    if not path.is_file():
      raise FileNotFoundError(f"Файл с токеном не найден: {token_file}")
    with open(path, "r") as f:
      self.token = f.readline().strip()
    if not self.token:
      raise ValueError("Файл с токеном пуст")
    
  def get_accounts(self) -> pd.DataFrame:
    with Client(self.token) as client:
      accounts = client.users.get_accounts().accounts
      return pd.DataFrame([{"ID": acc.id, "NAME": acc.name} for acc in accounts])
    
  def _get_account_id(self, name: str) -> str:
    accounts = self.get_accounts()
    match = accounts[accounts["NAME"] == name]
    if match.empty:
      raise ValueError(f"Счет с именем '{name}' не найден")
    return match.iloc[0]["ID"]
  
  def _get_figi(self, ticker: str) -> str:
    ticker = ticker.upper()
    with Client(self.token) as client:
      instruments = client.instruments.shares(
        instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE
      ).instruments
    inst = next((i for i in instruments if i.ticker == ticker), None)
    if inst is None:
      raise ValueError(f"FIGI для '{ticker}' не найдено")
    return inst.figi
  
  def _place_order( self, account: str, figi: str,
    quantity: int, direction: OrderDirection,
    price: float | None):

    if quantity <= 0:
      raise ValueError("Количество должно быть положительным.")

    order_type = (
      OrderType.ORDER_TYPE_MARKET
      if price is None
      else OrderType.ORDER_TYPE_LIMIT
    )

    price_q = None
    if price is not None:
      if price <= 0:
          raise ValueError("Цена должна быть положительной")
      price_q = decimal_to_quotation(price)

    with Client(self.token) as client:
      order = client.orders.post_order(
        figi=figi,
        quantity=quantity,
        account_id=account,
        direction=direction,
        order_type=order_type,
        price=price_q,
      )
    return order

  def buy(self, account: str, ticker: str, quantity: int, price: float = None):
    account_id = self._get_account_id(account)
    figi = self._get_figi(ticker)
    order = self._place_order(
      account=account_id,
      figi=figi,
      quantity=quantity,
      direction=OrderDirection.ORDER_DIRECTION_BUY,
      price=price,
    )

    return order.order_id
    
  def sell(self, account: str, ticker: str, quantity: int, price: float = None):
    account_id = self._get_account_id(account)
    figi = self._get_figi(ticker)
    order = self._place_order(
      account=account_id,
      figi=figi,
      quantity=quantity,
      direction=OrderDirection.ORDER_DIRECTION_SELL,
      price=price,
    )

    return  order.order_id
  
  def get_order_state(self, account: str, order_id: str) -> dict:
    account_id = self._get_account_id(account)
    with Client(self.token) as client:
      state = client.orders.get_order_state(
        account_id=account_id,
        order_id=order_id
      )
    return {
      "order_id": order_id,
      "status": state.execution_report_status.name,
      "executed_lots": state.lots_executed,
      "price": (
          float(quotation_to_decimal(state.executed_order_price))
          if state.executed_order_price else None
        )
    }

  def _place_stop_order(self, account_id: str, figi: str,
    quantity: int, stop_price: float, exec_price: float,
    direction: str, order_type: str) -> str:
    stop_order_type_map = {
      "STOP_LOSS": StopOrderType.STOP_ORDER_TYPE_STOP_LOSS,
      "TAKE_PROFIT": StopOrderType.STOP_ORDER_TYPE_TAKE_PROFIT,
    }
    if order_type not in stop_order_type_map:
      raise ValueError("order_type должен быть 'STOP_LOSS' или 'TAKE_PROFIT'")

    stop_q = decimal_to_quotation(Decimal(str(stop_price)))
    exec_q = decimal_to_quotation(Decimal(str(exec_price)))

    with Client(self.token) as client:
      resp = client.stop_orders.post_stop_order(
        account_id=account_id,
        figi=figi,
        quantity=quantity,
        stop_price=stop_q,
        price=exec_q,
        direction=StopOrderDirection.STOP_ORDER_DIRECTION_SELL
        if direction.upper() == "SELL"
        else StopOrderDirection.STOP_ORDER_DIRECTION_BUY,
        expiration_type=StopOrderExpirationType.STOP_ORDER_EXPIRATION_TYPE_GOOD_TILL_CANCEL,
        stop_order_type=stop_order_type_map[order_type],
      )
    return resp.stop_order_id

  def long_stop_loss(self, account: str, ticker: str, stop_price: float, exec_price: float, quantity: int):
    account_id = self._get_account_id(account)
    figi = self._get_figi(ticker)
    return self._place_stop_order(account_id, figi, quantity, stop_price, exec_price, "SELL", "STOP_LOSS")

  def long_take_profit(self, account: str, ticker: str, stop_price: float, exec_price: float, quantity: int):
    account_id = self._get_account_id(account)
    figi = self._get_figi(ticker)
    return self._place_stop_order(account_id, figi, quantity, stop_price, exec_price, "SELL", "TAKE_PROFIT")

  def short_stop_loss(self, account: str, ticker: str, stop_price: float, exec_price: float, quantity: int):
    account_id = self._get_account_id(account)
    figi = self._get_figi(ticker)
    return self._place_stop_order(account_id, figi, quantity, stop_price, exec_price, "BUY", "STOP_LOSS")

  def short_take_profit(self, account: str, ticker: str, stop_price: float, exec_price: float, quantity: int):
    account_id = self._get_account_id(account)
    figi = self._get_figi(ticker)
    return self._place_stop_order(account_id, figi, quantity, stop_price, exec_price, "BUY", "TAKE_PROFIT")

  def get_current_price(self, ticker: str) -> float:
    figi = self._get_figi(ticker)
    with Client(self.token) as client:
      orderbook = client.market_data.get_order_book(
        figi=figi,
        depth=1  
      )
    if orderbook.last_price is not None:
      return float(quotation_to_decimal(orderbook.last_price))
    
    bid_price = quotation_to_decimal(orderbook.bids[0].price) if orderbook.bids else None
    ask_price = quotation_to_decimal(orderbook.asks[0].price) if orderbook.asks else None

    if bid_price is not None and ask_price is not None:
      return float((bid_price + ask_price) / 2)
    elif bid_price is not None:
      return float(bid_price)
    elif ask_price is not None:
      return float(ask_price)
    else:
      raise ValueError(f"Невозможно получить текущую цену для '{ticker}'")