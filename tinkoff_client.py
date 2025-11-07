from tinkoff.invest import Client, CandleInterval
from tinkoff.invest import OrderDirection, OrderType, OrderExecutionReportStatus
from tinkoff.invest import StopOrderDirection, StopOrderExpirationType, StopOrderType
from tinkoff.invest.utils import quotation_to_decimal, decimal_to_quotation
from pathlib import Path
import pandas as pd
from datetime import datetime, timezone, timedelta
import time
from decimal import Decimal

class TinkoffClient:
    def __init__(self, token_file: str, ticker: str = None, account_name: str = None):
        path = Path(token_file)
        if not path.is_file():
            raise FileNotFoundError(f"Token file not found: {token_file}")
        with open(path, "r") as f:
            self.token = f.readline().strip()
        if not self.token:
            raise ValueError("Empty token!")
        self._ticker = None
        self._figi = None
        self._account_name = None
        self._account_id = None
        if ticker:
            self.ticker = ticker
        if account_name:
            self.account_name = account_name

    @property
    def ticker(self):
        return self._ticker

    @ticker.setter
    def ticker(self, value: str):
        with Client(self.token) as client:
            shares = client.instruments.shares().instruments
            instrument = next((s for s in shares if s.ticker == value), None)
            if instrument is None:
                raise ValueError(f"Stock '{value}' not found.")
            self._ticker = value
            self._figi = instrument.figi

    @property
    def figi(self):
        return self._figi

    @property
    def account_name(self):
        return self._account_name

    @account_name.setter
    def account_name(self, value: str):
        with Client(self.token) as client:
            accounts = client.users.get_accounts().accounts
            acc = next((a for a in accounts if a.name.lower() == value.lower()), None)
            if acc is None:
                available = [a.name for a in accounts]
                raise ValueError(f"Account '{value}' not found. Available: {available}")
            self._account_name = acc.name
            self._account_id = acc.id

    @property
    def account_id(self):
        return self._account_id

    def _wait_and_get_fill_price(self, order_id: str) -> float | None:
        with Client(self.token) as client:
            for _ in range(20):
                state = client.orders.get_order_state(account_id=self._account_id, order_id=order_id)
                status = state.execution_report_status
                if status == OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_FILL:
                    if state.executed_order_price:
                        return float(quotation_to_decimal(state.executed_order_price))
                    return None
                elif status in [OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_REJECTED,
                                OrderExecutionReportStatus.EXECUTION_REPORT_STATUS_CANCELLED]:
                    return None
                time.sleep(0.5)
        print(f"[WARN] Order {order_id} not filled after waiting.")
        return None

    def accounts_info(self) -> pd.DataFrame:
        with Client(self.token) as client:
            accounts = client.users.get_accounts().accounts
            return pd.DataFrame([{"ID": acc.id, "NAME": acc.name} for acc in accounts])

    def get_last_price(self) -> float:
        if not self._figi:
            raise ValueError("Ticker not set. Use client.ticker = 'SBER'")
        with Client(self.token) as client:
            prices = client.market_data.get_last_prices(figi=[self._figi]).last_prices
            price = float(quotation_to_decimal(prices[0].price))
        return price

    def get_history(self, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
        if not self._figi:
            raise ValueError("Ticker not set.")
        interval_map = {"1d": CandleInterval.CANDLE_INTERVAL_DAY,
                        "1h": CandleInterval.CANDLE_INTERVAL_HOUR,
                        "10m": CandleInterval.CANDLE_INTERVAL_10_MIN,
                        "1m": CandleInterval.CANDLE_INTERVAL_1_MIN}
        if interval not in interval_map:
            raise ValueError("interval must be one of: '1d', '1h', '10m', '1m'")
        MOSCOW_TZ = timezone(timedelta(hours=3))
        from_time = datetime.fromisoformat(start)
        to_time = datetime.fromisoformat(end)
        with Client(self.token) as client:
            candles = client.market_data.get_candles(figi=self._figi, from_=from_time,
                                                     to=to_time, interval=interval_map[interval]).candles
        if not candles:
            print(f"[INFO] No candles for {self._ticker} from {start} to {end}")
            return pd.DataFrame(columns=["TIMESTAMP", "PRICE"])
        df = pd.DataFrame([{"TIMESTAMP": c.time.astimezone(MOSCOW_TZ),
                            "PRICE": float(quotation_to_decimal(c.close))} for c in candles])
        return df

    def fetch_prices(self, n: int = 10, interval: str = "1m") -> pd.DataFrame:
        if not self._figi:
            raise ValueError("Ticker not set.")

        interval_map = {
            "1d": CandleInterval.CANDLE_INTERVAL_DAY,
            "1h": CandleInterval.CANDLE_INTERVAL_HOUR,
            "10m": CandleInterval.CANDLE_INTERVAL_10_MIN,
            "1m": CandleInterval.CANDLE_INTERVAL_1_MIN,
        }
        if interval not in interval_map:
            raise ValueError("interval must be one of: '1d', '1h', '10m', '1m'")

        to_time = datetime.now(tz=timezone.utc)
        if interval == "1d":
            delta = timedelta(days=n)
        elif interval == "1h":
            delta = timedelta(hours=n)
        elif interval == "10m":
            delta = timedelta(minutes=10 * n)
        elif interval == "1m":
            delta = timedelta(minutes=n)
        from_time = to_time - delta

        MOSCOW_TZ = timezone(timedelta(hours=3))

        with Client(self.token) as client:
            candles = client.market_data.get_candles(
                figi=self._figi,
                from_=from_time,
                to=to_time,
                interval=interval_map[interval],
            ).candles

        data = [
            {
                "TIMESTAMP": c.time.astimezone(MOSCOW_TZ),
                "PRICE": float(quotation_to_decimal(c.close)),
            }
            for c in candles
        ]

        df = pd.DataFrame(data)
        df.sort_values("TIMESTAMP", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def buy(self, quantity: int, price: float = None):
        if not self._figi or not self._account_id:
            raise ValueError("Ticker or account not set.")
        with Client(self.token) as client:
            order_type = OrderType.ORDER_TYPE_MARKET if price is None else OrderType.ORDER_TYPE_LIMIT
            price_val = None if price is None else decimal_to_quotation(price)
            order = client.orders.post_order(figi=self._figi, quantity=quantity, account_id=self._account_id,
                                             direction=OrderDirection.ORDER_DIRECTION_BUY,
                                             order_type=order_type, price=price_val)
        if price is None:
            price = self._wait_and_get_fill_price(order.order_id)
        print(f"[BUY] Order {order.order_id} | Qty: {quantity} | Price: {price} | Type: {order_type.name}")

    def sell(self, quantity: int, price: float = None):
        if not self._figi or not self._account_id:
            raise ValueError("Ticker or account not set.")
        with Client(self.token) as client:
            order_type = OrderType.ORDER_TYPE_MARKET if price is None else OrderType.ORDER_TYPE_LIMIT
            price_val = None if price is None else decimal_to_quotation(price)
            order = client.orders.post_order(figi=self._figi, quantity=quantity, account_id=self._account_id,
                                             direction=OrderDirection.ORDER_DIRECTION_SELL,
                                             order_type=order_type, price=price_val)
        if price is None:
            price = self._wait_and_get_fill_price(order.order_id)
        print(f"[SELL] Order {order.order_id} | Qty: {quantity} | Price: {price} | Type: {order_type.name}")

    def place_stop_order(self, stop_price: float, exec_price: float, quantity: int,
                         direction: str = "SELL", order_type: str = "STOP_LOSS"):
        if not self._figi or not self._account_id:
            raise ValueError("Ticker or account not set")
        stop_order_type_map = {"STOP_LOSS": StopOrderType.STOP_ORDER_TYPE_STOP_LOSS,
                               "TAKE_PROFIT": StopOrderType.STOP_ORDER_TYPE_TAKE_PROFIT}
        if order_type not in stop_order_type_map:
            raise ValueError("order_type must be 'STOP_LOSS' or 'TAKE_PROFIT'")
        stop_price_q = decimal_to_quotation(Decimal(str(stop_price)))
        exec_price_q = decimal_to_quotation(Decimal(str(exec_price)))
        with Client(self.token) as client:
            resp = client.stop_orders.post_stop_order(account_id=self._account_id, figi=self._figi,
                                                      quantity=quantity, stop_price=stop_price_q,
                                                      price=exec_price_q,
                                                      direction=(StopOrderDirection.STOP_ORDER_DIRECTION_SELL
                                                                 if direction.upper() == "SELL"
                                                                 else StopOrderDirection.STOP_ORDER_DIRECTION_BUY),
                                                      expiration_type=StopOrderExpirationType.STOP_ORDER_EXPIRATION_TYPE_GOOD_TILL_CANCEL,
                                                      stop_order_type=stop_order_type_map[order_type])
        print(f"[STOP] {order_type} {direction} | Qty: {quantity} | Stop: {stop_price} | Limit: {exec_price}")
        return resp.stop_order_id

    def long_stop_loss(self, stop_price: float, exec_price: float, quantity: int):
        return self.place_stop_order(stop_price, exec_price, quantity, direction="SELL", order_type="STOP_LOSS")

    def long_take_profit(self, stop_price: float, exec_price: float, quantity: int):
        return self.place_stop_order(stop_price, exec_price, quantity, direction="SELL", order_type="TAKE_PROFIT")

    def short_stop_loss(self, stop_price: float, exec_price: float, quantity: int):
        return self.place_stop_order(stop_price, exec_price, quantity, direction="BUY", order_type="STOP_LOSS")

    def short_take_profit(self, stop_price: float, exec_price: float, quantity: int):
        return self.place_stop_order(stop_price, exec_price, quantity, direction="BUY", order_type="TAKE_PROFIT")
    
    def check_status(self, order_id: str) -> bool:
        with Client(self.token) as client:
            active_stops = client.stop_orders.get_stop_orders(account_id=self._account_id).stop_orders
            if any(s.stop_order_id == order_id for s in active_stops):
                return False           
        return True