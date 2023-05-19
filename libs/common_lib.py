import math
from ..libs import parser_lib as parsLib
from ..libs import rest_lib as restLib

# CONSTANTS
API_BASE_URL = "https://api.bitopro.com/v3"

ACTIONS = {
        "buy": "BUY",
        "sell": "SELL"
        }

LOG_TO_CONSOLE = True

ORDER_STATUS = {
        "-1": "Not Triggered",
        "0": "In Progress",
        "1": "In Progress (partial deal)",
        "2": "Completed",
        "3": "Completed (partial deal)",
        "4": "Cancelled",
        "6": "Post-only cancelled"
        }

PAIRS = {
        "ADA": "ada_twd",
        "BTC": "btc_twd",
        "ETH": "eth_twd",
        "SOL": "sol_twd"
        }

PAUSE_CHECK_INTERVAL = 60 * 10 # pause API access for 10 minutes

SELL_CHECK_FREQUENCY = 5 # 5 seconds


# FUNCTIONS
def round_down(quantity: float) -> float:
    """
    params:
        - quantity (float): value which to round down
    performs:
        - rounds down to 8 decimals of precision to avoid the rounding up inherent in the math library's round function
    returns:
        - (float): the rounded value
    """
    return math.floor(quantity * 100_000_000) / 100_000_000


def get_available_twd_balance() -> float:
    """
    params:
        - None
    performs:
        - fetches and parses the available amount of dry powder (in TWD) 
    returns: 
        - (float): avaialble amount of dry powder (in TWD)
    """
    try:
        acctBalances = restLib.get_balance()
        twdBalance, _ = parsLib.parse_balance(acctBalances, "twd")
    except Exception as e:
        raise Exception(f"common_lib:_get_available_twd_balance(): {e}")
    
    return twdBalance


