# CONSTS
API_BASE_URL = "https://api.bitopro.com/v3"

ACTIONS = {
        "buy": "BUY",
        "sell": "SELL"
        }

PAIRS = {
        "ADA": "ada_twd",
        "BTC": "btc_twd",
        "ETH": "eth_twd",
        "SOL": "sol_twd"
        }

ORDER_STATUS = {
        "-1": "Not Triggered",
        "0": "In Progress",
        "1": "In Progress (partial deal)",
        "2": "Completed",
        "3": "Completed (partial deal)",
        "4": "Cancelled",
        "6": "Post-only cancelled"
        }

LOG_TO_CONSOLE = False
