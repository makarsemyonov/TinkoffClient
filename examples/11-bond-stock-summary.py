from tinkoff_client import TinkoffClient

cli = TinkoffClient("TOKEN.txt")

cli.portfolio.stocks_summary("Акции")
cli.portfolio.bonds_summary("Облигации")
