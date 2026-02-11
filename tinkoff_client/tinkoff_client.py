import pandas as pd
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta

from tinkoff.invest import Client, InstrumentIdType
from tinkoff.invest import CandleInterval
from tinkoff.invest import InstrumentStatus
from tinkoff.invest import OrderDirection, OrderType
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation
from tinkoff.invest import StopOrderDirection, StopOrderExpirationType, StopOrderType


class TinkoffClient:

  _INTERVAL_MAP = {
    "1m": CandleInterval.CANDLE_INTERVAL_1_MIN,
    "5m": CandleInterval.CANDLE_INTERVAL_5_MIN,
    "15m": CandleInterval.CANDLE_INTERVAL_15_MIN,
    "1h": CandleInterval.CANDLE_INTERVAL_HOUR,
    "1d": CandleInterval.CANDLE_INTERVAL_DAY,
    "1w": CandleInterval.CANDLE_INTERVAL_WEEK,
    "1mo": CandleInterval.CANDLE_INTERVAL_MONTH,
  }

  _OPERATION_TYPE_MAP = {
    "OPERATION_TYPE_BUY": "BUY",
    "OPERATION_TYPE_SELL": "SELL",
    "OPERATION_TYPE_BROKER_FEE": "FEE",
    "OPERATION_TYPE_INP_MULTI": "DEPOSIT",
    "OPERATION_TYPE_OUT_MULTI": "WITHDRAW",
  }

  def __init__(self, token_file: str):
    path = Path(token_file)
    if not path.is_file():
      raise FileNotFoundError(f"Файл с токеном не найден: {token_file}")
    with open(path, "r") as f:
      self.token = f.readline().strip()
    if not self.token:
      raise ValueError("Файл с токеном пуст")
    
  def get_accounts(self) -> pd.DataFrame:
    rows = []
    with Client(self.token) as client:
      accounts = client.users.get_accounts().accounts
      for acc in accounts:
        portfolio = client.operations.get_portfolio(account_id=acc.id)
        balance = (
          float(portfolio.total_amount_portfolio.units)
          + float(portfolio.total_amount_portfolio.nano) / 1e9
        )
        rows.append({
          "ID": acc.id,
          "NAME": acc.name,
          "OPENED_AT": acc.opened_date.date() if acc.opened_date else None,
          "BALANCE_RUB": balance
        })
    return pd.DataFrame(rows)
    
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
  
  def _get_ticker(self, figi: str) -> str:
    if not figi:
        return None
    with Client(self.token) as client:
      instr = client.instruments.get_instrument_by(
        id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
        id=figi
      ).instrument

    if not instr or not instr.ticker:
      raise ValueError(f"Инструмент с FIGI {figi} не найден или тикер отсутствует")
    return instr.ticker
  
  def _quotation_to_float(self, q):
    if q is None:
        return 0.0
    if hasattr(q, "units") and hasattr(q, "nano") and q.units == 0 and q.nano == 0:
        return 0.0
    return float(quotation_to_decimal(q))

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
  

  def get_history(self, ticker: str, from_date: datetime,
    to_date: datetime, interval: str = "1d") -> pd.DataFrame:

    figi = self._get_figi(ticker)

    if interval not in self._INTERVAL_MAP:
      raise ValueError(
        f"Interval '{interval}' не поддерживается. "
        f"Доступные: {list(self._INTERVAL_MAP.keys())}"
      )

    ti_interval = self._INTERVAL_MAP[interval]

    max_range = {
      "1m": timedelta(days=1),
      "5m": timedelta(days=7),
      "15m": timedelta(days=30),
      "1h": timedelta(days=30),
      "1d": timedelta(days=365),
      "1w": timedelta(days=365 * 5),
      "1mo": timedelta(days=365 * 10),
    }

    step = max_range.get(interval)

    all_rows = []

    cur_from = from_date

    with Client(self.token) as client:
      while cur_from < to_date:
        cur_to = min(cur_from + step, to_date)

        candles = client.market_data.get_candles(
          figi=figi,
          from_=cur_from,
          to=cur_to,
          interval=ti_interval,
        ).candles

        for c in candles:
          all_rows.append({
            "time": c.time,
            "open": float(c.open.units + c.open.nano / 1e9),
            "high": float(c.high.units + c.high.nano / 1e9),
            "low": float(c.low.units + c.low.nano / 1e9),
            "close": float(c.close.units + c.close.nano / 1e9),
            "volume": c.volume,
          })

        cur_from = cur_to

    if not all_rows:
      return pd.DataFrame(
        columns=["time", "open", "high", "low", "close", "volume"]
    )

    return (
      pd.DataFrame(all_rows)
      .drop_duplicates(subset="time")
      .sort_values("time")
      .reset_index(drop=True)
    )


  def get_operations_history(self, account: str, from_date: datetime, to_date: datetime) -> pd.DataFrame:
    account_id = self._get_account_id(account)

    with Client(self.token) as client:
      ops = client.operations.get_operations(
        account_id=account_id,
        from_=from_date,
        to=to_date,
      ).operations

    rows = []
    for op in ops:
      rows.append({
        "time": op.date,
        "type": self._OPERATION_TYPE_MAP.get(op.operation_type.name),
        "ticker": self._get_ticker(op.figi),
        "quantity": op.quantity,
        "price": self._quotation_to_float(op.price),
        "payment": self._quotation_to_float(op.payment),
      })
    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True)
  
  def get_positions(self, account: str) -> pd.DataFrame:
    account_id = self._get_account_id(account)

    rows = []

    with Client(self.token) as client:
      portfolio = client.operations.get_portfolio(account_id=account_id)
      for pos in portfolio.positions:
        quantity = self._quotation_to_float(pos.quantity)
        avg_price = self._quotation_to_float(pos.average_position_price)
        current_price = self._quotation_to_float(pos.current_price)
        expected_yield = self._quotation_to_float(pos.expected_yield)
        return_pct = (
          (current_price - avg_price) / avg_price * 100
          if avg_price > 0 else 0.0
        )

        rows.append({
          "figi": pos.figi,
          "ticker": self._get_ticker(pos.figi) if pos.figi else None,
          "instrument_type": pos.instrument_type,
          "quantity": quantity,
          "average_price": avg_price,
          "current_price": current_price,
          "expected_yield": expected_yield,
          "return_pct": return_pct,
        })

    df = pd.DataFrame(rows)

    if df.empty:
      return df

    return df.sort_values("expected_yield", ascending=False).reset_index(drop=True)
