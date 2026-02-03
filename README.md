# TinkoffClient

Python-клиент для работы с API Tinkoff Invest.

## Доступный функционал:
- Получение счетов пользователя
- Получение текущей цены по тикеру
- Выставление рыночных и лимитных ордеров
- Проверка статуса рыночных и лимитных ордеров
- Выставление стоп-ордеров (стоп-лосс и тейк-профит)

## Установка

Требуется Python >=3.10

```bash
git clone https://github.com/makarsemyonov/TinkoffClient.git
cd TinkoffClient
pip install .
```

## Использование
1. Создайте файл TOKEN.txt и вставьте в него ваш токен Tinkoff Invest.
2. Импортируйте и создайте объект клиента:

```python
from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")
```

