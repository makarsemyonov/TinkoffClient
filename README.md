# Tinkoff Client

Класс `TinkoffClient` предоставляет удобный интерфейс для работы с API Тинькофф Инвестиций.  
Реализует функционал создания рыночных и лимитных ордеров, стоп-заявок (Stop Loss / Take Profit). Так же предоставляет возможность получить исторические данные и текущие цены.

---

## Поля

- `ticker` — тикер текущего инструмента. Сеттер автоматически обновляет FIGI.
- `figi` — FIGI инструмента.
- `account_name` — имя счета. Сеттер автоматически обновляет ID.
- `account_id` — ID счета.

---

## Методы

### `Конструктор TinkoffClient(token_file: str, ticker: str = None, account_name: str = None)`

- token_file — путь к файлу с API-токеном

- ticker — тикер инструмента (необязательно)

- account_name — имя счёта (необязательно)

При задании ticker и/или account_name автоматически подгружаются FIGI и/ ID счёта.

---

### `ticker() -> str`

Возвращает текущий тикер.

---

### `ticker(value: str)`

Устанавливает тикер и автоматически обновляет FIGI.  

---

### `figi() -> str`

Возвращает FIGI текущего тикера. Только геттер.

---

### `account_name() -> str`

Возвращает имя текущего счета.

---

### `account_name(value: str)`

Устанавливает имя счета и автоматически обновляет ID.  

---

### `account_id() -> str`

Возвращает ID текущего счета. 

---

### `accounts_info() -> pd.DataFrame`

Возвращает список всех счетов пользователя.  

---

### `get_last_price() -> float`

Возвращает последнюю цену текущего тикера.

---

### `get_history(start: str, end: str, interval: str = "1d") -> pd.DataFrame`

Получает исторические цены за указанный период.  

- `start`, `end` — даты в формате `YYYY-MM-DD`
- `interval` — `"1d"`, `"1h"`, `"10m"`, `"1m"`

---

 ### `fetch_prices(self, n: int = 10, interval: str = "1m") -> pd.DataFrame`

 Возвращает последние n цен инструмента по заданному интервалу.

 Доступые интервалы — `"1d"`, `"1h"`, `"10m"`, `"1m"`

---

### `buy(quantity: int, price: float = None)`

Создаёт лимитный или рыночный ордер на покупку.  

- `quantity` — количество лотов
- `price` — цена (если `None`, создается рыночный ордер)

Возвращает цену исполнения для рыночного ордера.

---

### `sell(quantity: int, price: float = None)`

Создаёт лимитный или рыночный ордер на продажу.  

- `quantity` — количество лотов
- `price` — цена (если `None`, создается рыночный ордер)

Возвращает цену исполнения для рыночного ордера.

---

### `place_stop_order(stop_price: float, exec_price: float, quantity: int, direction: str = "SELL", order_type: str = "STOP_LOSS")`

Универсальная функция для выставления стоп-заявок.  

- `stop_price` — цена активации (триггер)
- `exec_price` — лимитная цена после срабатывания стопа
- `quantity` — количество лотов
- `direction` — `"SELL"` или `"BUY"`
- `order_type` — `"STOP_LOSS"` или `"TAKE_PROFIT"`

Возвращает `stop_order_id`.

---

### Удобные обертки для стоп-заявок

- `long_stop_loss(stop_price, exec_price, quantity)` — стоп-лосс для длинной позиции
- `long_take_profit(stop_price, exec_price, quantity)` — тейк-профит для длинной позиции
- `short_stop_loss(stop_price, exec_price, quantity)` — стоп-лосс для короткой позиции
- `short_take_profit(stop_price, exec_price, quantity)` — тейк-профит для короткой позиции

---

## Пример использования

Купить акцию Сбера и выставить TP/SL:

```python
from tinkoff_client import TinkoffClient

client = TinkoffClient("TOKEN.txt", "SBER", "Stocks")

print(client.get_last_price())

client.buy(quantity=1)

client.long_stop_loss(stop_price=300.0, exec_price=299.0, quantity=1)
client.long_take_profit(stop_price=310.0, exec_price=309.0, quantity=1)
```
