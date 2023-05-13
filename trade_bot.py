"""
----------
HOW TO RUN
----------
from parent directory:
    $ python3 -m TradeBot.trade_bot

----------
EXAMPLES OF HOW TO USE AS A STAND ALONE IMPORT IN THE PYTHON INTERPRETER
----------
SETUP
> import trade_bot as tb

> acctBalances = tb.get_balance()
> assetBalance, _ = tb.parse_balance(acctBalances, "ada")

> pair = common.PAIRS["ADA"]
> price, _ = tb.parse_ticker_price(tb.get_asset_price(pair))

> mostRecentOrderId, _ = tb.parse_orders(tb.get_orders(pair))

CANCEL
> tb.cancel_order(pair, mostRecentOrderId)

BUY
> tb.create_order(Order(pair, common.ACTIONS["buy"], "limit", assetBalance/price, price))

SELL
> price *= 1.02 # or *= 0.98
> tb.create_order(Order(pair, common.ACTIONS["sell"], "limit", assetBalance, price))

ORDER BOOK
> order_book = tb.get_book_order_price(pair)
> tb.parse_order_book_orders(order_book, price, assetBalance, True)
"""

import requests
import time
import threading
from . import common
from datetime import datetime
from .entities.logger import *
from .entities.authenticator import *
from .entities.order import Order
from .entities.price_checker import *
from .entities.strategy import *
from typing import List, Tuple

# ------------------------------------
# CONSTS
LOG_TO_CONSOLE = False


# ------------------------------------
# NECESSARY BASIC DATA
authenticator = Authenticator()
logger = create_logger()


# ------------------------------------
# REST FUNCTIONS
# GET
def get_balance() -> List[object]:
    """
    params: None
    performs: gets list of all current balances for all assets
    returns: list of all balances as dictionaries
    """
    endpoint = "/accounts/balance"
    response = requests.get(common.API_BASE_URL+endpoint, headers=create_default_headers())


    if response.status_code != 200:
        logger.program(f"trade_bot:get_balance(): status_code: {response.status_code}")
        if LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_balance() status_code: {response.status_code}\n")

    try:
        return response.json()["data"]
    except Exception as e:
        raise Exception(f"trade_bot:get_balance(): Unparsable JSON; check response status code: {e}")


def get_orders(pair: str) -> List[object]:
    """
    params: order pair
    performs: gets list of all orders for specified asset for last 90 days
    returns: list of all orders as dictionaries
    """
    endpoint = f"/orders/all/{pair}"
    response = requests.get(common.API_BASE_URL+endpoint, headers=create_default_headers())

    if response.status_code != 200:
        logger.program(f"trade_bot:get_orders(): status_code: {response.status_code}")
        if LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_orders() status_code: {response.status_code}\n")

    try:
        return response.json()["data"]
    except Exception as e:
        raise Exception(f"trade_bot:get_orders(): Unparsable JSON; check response status code: {e}")

def get_order_by_id(pair: str, orderId: str) -> object:
    """
    params: order pair; orderId
    performs: gets a specified order for specified asset for last 90 days
    returns: order as dictionaries
    """
    endpoint = f"/orders/{pair}/{orderId}"
    response = requests.get(common.API_BASE_URL+endpoint, headers=create_default_headers())

    if response.status_code != 200:
        logger.program(f"trade_bot:get_order_by_id(): status_code: {response.status_code}")
        if LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_order_by_id() status_code: {response.status_code}\n")

    try:
        return response.json()
    except Exception as e:
        raise Exception(f"trade_bot:get_order_by_id(): Unparsable JSON; check response status code: {e}")


def get_asset_price(pair: str) -> float:
    """
    params: trading pair (e.g., btc_twd)
    performs: gets most recent price for specified trading pair
    returns: price as a float
    """
    endpoint = f"/tickers/{pair}"
    response = requests.get(common.API_BASE_URL+endpoint, headers=create_default_headers())

    if response.status_code != 200:
        logger.program(f"trade_bot:get_asset_price(): status_code: {response.status_code}")
        if LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_asset_price() status_code: {response.status_code}\n")

    try:
        return response.json()["data"]
    except Exception as e:
        raise Exception(f"trade_bot:get_asset_price(): Unparsable JSON; check response status code: {e}")


def get_book_order_price(pair: str) -> object:
    """
    params: trading pair (e.g., btc_twd)
    performs: gets most recent book order price for specified asset
    returns: bids and asks as a dictionary
    """
    endpoint = f"/order-book/{pair}?limit=10"
    response = requests.get(common.API_BASE_URL+endpoint)

    if response.status_code != 200:
        logger.program(f"trade_bot:get_book_order_price(): status_code: {response.status_code}")
        if LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_book_order_price() status_code: {response.status_code}\n")

    try:
        return response.json()
    except Exception as e:
        raise Exception(f"trade_bot:get_book_order_price(): Unparsable JSON; check response status code: {e}")


# DELETE
def cancel_order(pair: str, orderId: str) -> int:
    """
    params: order pair; id of the order to cancel
    performs: cancels an existing order
    returns: response status code
    """
    endpoint = f"/orders/{pair}/{orderId}"
    response = requests.delete(common.API_BASE_URL+endpoint, headers=create_default_headers())

    if response.status_code != 200:
        logger.program(f"trade_bot:cancel_order(): status_code: {response.status_code}")
        if LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"cancel_order() status_code: {response.status_code}\n")

    logger.trades(f"Cancelled Order #{orderId}")

    return response.status_code


# POST
def create_order(order: Order) -> Tuple[str, int]:
    """
    params: an order object for a specific pair
    function: post a new limit-order request for the given order
    returns: tuple of order ID and response status code
    """
    orderId = ""
    endpoint = f"/orders/{order.get_pair()}"
    body = build_order_body(order)
    response = requests.post(common.API_BASE_URL+endpoint, headers=create_order_headers(body), data=body)

    if response.status_code != 200:
        logger.program(f"trade_bot:create_order(): status_code: {response.status_code}")
        if LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"create_order() status_code: {response.status_code}\n")

    try:
        if LOG_TO_CONSOLE:
            print(response.json())

        result = response.json()
        orderId = result["id"]

        logStr = f"\nID: {result['id']}\n" 
        logStr += f"action: {result['action']}\n" 
        logStr += f"type: {result['type']}\n"
        logStr += f"Limit-Order Price: {result['price']}\n"
        logStr += f"Last updated: {datetime.fromtimestamp(int(result['updatedTimestamp']/1000))}\n"
        logStr += f"Order status: {common.ORDER_STATUS[str(result['status'])]}"
        logger.trades(logStr)
    except Exception as e:
        raise Exception(f"trade_bot:create_order(): Unparsable JSON; check response status code: {e}")
    finally:
        return (orderId, response.status_code)



# ------------------------------------
# HELPER FUNCTIONS
# HEADERS BUILDERS
def create_default_headers() -> object:
    """
    params: None
    performs: creates the headers required for authenticated actions (GET & DELETE)
    returns: headers as a dictionary
    """
    nonce = int(time.time() * 1000)
    payload = authenticator.get_encoded_payload("{\"identity\": \"santa.edwina@gmail.com\",\"nonce\": " + f"{nonce}" + "}")
    signature = authenticator.get_signature(payload) 

    return {
            "X-BITOPRO-APIKEY": authenticator.get_api_key(),
            "X-BITOPRO-PAYLOAD": payload,
            "X-BITOPRO-SIGNATURE": signature
            }


def create_order_headers(body: str) -> object:
    """
    params: payload body as a str
    performs: creates the headers required for authenticated actions (POST)
    returns: headers as a dictionary
    """
    payload = authenticator.get_encoded_payload(body)
    signature = authenticator.get_signature(payload) 

    return {
            "X-BITOPRO-APIKEY": authenticator.get_api_key(),
            "X-BITOPRO-PAYLOAD": payload,
            "X-BITOPRO-SIGNATURE": signature 
            }


# BODY BUILDERS
def build_order_body(order: Order, priceRoundingNumber: int = 4) -> str:
    """
    params: an order object for a specific asset for a regular limit-order
    performs: creates a json formatted string for the body of the HTTP request
    returns: json body as str
    """
    nonce = int(time.time() * 1000) # get current time; *1000 & cast to int because Python is special and uses floats instead of longs...
    amount = round(order.get_available_balance(), 8) # order amount can be at most 8 decimal places long
    price = round(order.get_hi_price(), priceRoundingNumber) # order prices can be at most 4 decimal places long
    body = "{" + f"\"action\": \"{order.get_action()}\"," + f"\"amount\": \"{amount}\"," + f"\"price\": \"{price}\"," + f"\"timestamp\": {nonce}," + f"\"type\": \"{order.get_order_type()}\"" + "}"

    return body


# PARSERS
def parse_orders(orders: List[object]) -> Tuple[str, int]:
    """
    params: a list of orders from a specific asset
    performs: prints order info
    returns: tuple of orderId as a str and order status as int
    """
    # sort orders by timestamp
    sorted_orders = sorted(orders, key=lambda x: x["createdTimestamp"])
    order = sorted_orders[-1] # sorted in ascending order, so most recent is the last in the last

    logStr = f"ID: {order['id']}\n" + f"action: {order['action']}\n" + f"type: {order['type']}\n"
    logStr += f"Limit-Order Price: {order['price']}\n" 
    if order["type"] == "STOP_LIMIT":
        logStr += f"Stop-Loss Price: {order['stopPrice']}\n"
    logStr += f"Last updated: {datetime.fromtimestamp(int(order['updatedTimestamp']/1000))}\n"
    logStr += f"Order status: {common.ORDER_STATUS[str(order['status'])]}"
    
    if LOG_TO_CONSOLE and common.ORDER_STATUS[str(order["status"])] == "In Progress":
        print(order)

    return (order["id"], order["status"])


def parse_order_total(order: object) -> Tuple[float, int]:
    """
    params: an order from a specific asset
    performs: extracts total amount of order 
    returns: tuple of total amount as float and order status as int
    """
    logStr = f"ID: {order['id']}\n" + f"action: {order['action']}\n" + f"type: {order['type']}\n"
    logStr += f"Avg-Execution Price: {order['avgExecutionPrice']}\n" 
    logStr += f"Original Amount: {order['originalAmount']}"
    logStr += f"Executed Amount: {order['executedAmount']}"
    logStr += f"Last updated: {datetime.fromtimestamp(int(order['updatedTimestamp']/1000))}\n"
    logStr += f"Order status: {common.ORDER_STATUS[str(order['status'])]}"
    
    if LOG_TO_CONSOLE and common.ORDER_STATUS[str(order["status"])] == "In Progress":
        print(order)

    return (float(order["avgExecutionPrice"]) * float(order["executedAmount"]), order["status"])


def parse_balance(balances: List[object], asset: str) -> Tuple[float, float]:
    """
    params: a list of balances in acct; a specific asset whose balance is of interest
    performs: prints balance info of all current balances
    returns: available and total balances for asset as a floats
    """
    availableBalance =  0.0
    totalBalance =  0.0
    for balance in balances:
        if balance["currency"] == asset:
            if LOG_TO_CONSOLE:
                print(f"{balance['currency']}: \n\ttotal = {balance['amount']} \n\tavailable = {balance['available']}")

            availableBalance = float(balance["available"])
            totalBalance = float(balance["amount"])

    return (availableBalance, totalBalance)


def parse_ticker_price(tickerObj: object) -> Tuple[float, float]:
    """
    params: a ticker of a specific asset
    performs: prints last sale price
    returns: lastPrice and 24hr delta as a floats
    """
    if LOG_TO_CONSOLE:
        print(f"Last price for {tickerObj['pair']} was: {float(tickerObj['lastPrice']):.2f}TWD")
        print(f"24-delta: {tickerObj['priceChange24hr']}%")

    return (float(tickerObj['lastPrice']), float(tickerObj['priceChange24hr']))


def parse_order_book_orders(orderBook: object, targetPrice: float, amount: float, parseBids: bool) -> float:
    """
    NOTE: bids = buyers; asks = sellers
    params: two lists of orders (bids & asks); the price which to compare the orders to; the amount of an asset which to compare the orders to; whether or not to parse the bids or the asks
    performs: compares the orders' prices and amounts to target values for trade
    returns: the best price to set the order at so that it can be filled ASAP; -1.0 if no satisfactory order is found
    """
    if parseBids:
        for bid in orderBook["bids"]:
            if float(bid["price"]) >= targetPrice and float(bid["amount"]) >= amount: 
                return float(bid["price"])
    else:
        for ask in orderBook["asks"]:
            if float(ask["price"]) <= targetPrice and float(ask["amount"]) >= amount: 
                return float(ask["price"])

    return -1.0


# ------------------------------------
# MAIN
# ------------------------------------
if __name__ == "__main__":
    """
    LOG_TO_CONSOLE = True

    pair = common.PAIRS["ADA"]
    mostRecentOrderId, _ = parse_orders(get_orders(pair))
    print(parse_order_total(get_order_by_id(pair, mostRecentOrderId)))


    LOG_TO_CONSOLE = True

    acctBalances = get_balance()
    assetBalance, _ = parse_balance(acctBalances, "ada")

    pair = common.PAIRS["ADA"]
    price, _ = parse_ticker_price(get_asset_price(pair))

    mostRecentOrderId, _ = parse_orders(get_orders(pair))
"""
    print("\n------------------")
    print("INITIATING PROGRAM")
    print("------------------")

    pair = common.PAIRS["ADA"]

    print("\n------------------")
    print("LOADING STRATEGY")

    priceChecker = PriceChecker(logger)
    strategy = Strategy(logger, principal=1000.0)

    print("\n------------------")
    print("CREATING THREADS")

    buyThread = threading.Thread(target=strategy.handle_buys, args=[pair])
    sellThread = threading.Thread(target=strategy.handle_sales, args=[pair])

    print("\n------------------")
    print("EXECUTING THREADS")

    buyThread.start()
    sellThread.start()

    buyThread.join()
    sellThread.join()

    print("\n------------------")
    print("TERMINATING PROGRAM")
    print("------------------") 
