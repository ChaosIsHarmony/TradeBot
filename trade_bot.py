import logging
import requests
import time
from datetime import datetime
from entities.authenticator import *
from entities.order import Order
from typing import List


# ------------------------------------
# NECESSARY BASIC DATA
# AUTHENTICATOR
authenticator = Authenticator()

# CUSTOM LOGGER
TRADES_LOG_LEVEL = 7
PROGRAM_LOG_LEVEL = 8
PRICE_LOG_LEVEL = 9

class CustomLogger(logging.getLoggerClass()):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        logging.addLevelName(TRADES_LOG_LEVEL, "TRADES")
        logging.addLevelName(PROGRAM_LOG_LEVEL, "PROGRAM")
        logging.addLevelName(PRICE_LOG_LEVEL, "PRICE")


    def trades(self, message, *args, **kws):
        self._log(TRADES_LOG_LEVEL, message, args, **kws)

    def program(self, message, *args, **kws):
        self._log(PROGRAM_LOG_LEVEL, message, args, **kws)

    def price(self, message, *args, **kws):
        self._log(PRICE_LOG_LEVEL, message, args, **kws)


logger = CustomLogger(__name__)

tradesHandler = logging.FileHandler("logs/trades.log")
programHandler = logging.FileHandler("logs/program.log")
priceHandler = logging.FileHandler("logs/price.log")

tradesFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
programFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
priceFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

tradesHandler.setFormatter(tradesFormatter)
programHandler.setFormatter(programFormatter)
priceHandler.setFormatter(priceFormatter)

tradesHandler.setLevel(TRADES_LOG_LEVEL)
programHandler.setLevel(PROGRAM_LOG_LEVEL)
priceHandler.setLevel(PRICE_LOG_LEVEL)

def program_filter(record):
    return not record.levelno == PROGRAM_LOG_LEVEL

def price_filter(record):
    return not record.levelno == PRICE_LOG_LEVEL

tradesHandler.addFilter(program_filter)
tradesHandler.addFilter(price_filter)
programHandler.addFilter(price_filter)

logger.addHandler(tradesHandler)
logger.addHandler(programHandler)
logger.addHandler(priceHandler)

"""
HOW TO USE
logger.trades("This is a trade log message")
logger.program("This is a program log message")
"""


# CONSTS
API_BASE_URL = "https://api.bitopro.com/v3"

UPSIDE_DELTA = 1.02
DOWNSIDE_DELTA = 0.98

ACTIONS = {
        "buy": "BUY",
        "sell": "SELL"
        }

PAIRS = {
        "ADA": "ada_twd",
        "BTC": "btc_twd",
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
    response = requests.get(API_BASE_URL+endpoint, headers=create_default_headers())

    print("\n------------------")
    print(f"get_balance() status_code: {response.status_code}\n")
    try:
        return response.json()["data"]
    except:
        raise Exception("Unparsable JSON; check response status code")



def get_orders(pair: str) -> List[object]:
    """
    params: order pair
    performs: gets list of all orders for specified asset for last 90 days
    returns: list of all orders as dictionaries
    """
    endpoint = f"/orders/all/{pair}"
    response = requests.get(API_BASE_URL+endpoint, headers=create_default_headers())

    print("\n------------------")
    print(f"get_orders() status_code: {response.status_code}\n")
    try:
        return response.json()["data"]
    except:
        raise Exception("Unparsable JSON; check response status code")



def get_asset_price(pair: str) -> float:
    """
    params: order pair
    performs: gets most recent price for specified asset
    returns: price as a float
    """
    endpoint = f"/tickers/{pair}"
    response = requests.get(API_BASE_URL+endpoint, headers=create_default_headers())

    print("\n------------------")
    print(f"get_asset_price() status_code: {response.status_code}\n")
    try:
        return response.json()["data"]
    except:
        raise Exception("Unparsable JSON; check response status code")


def get_book_order_price(pair: str) -> object:
    """
    params: order pair
    performs: gets most recent book order price for specified asset
    returns: bids and asks as a dictionary
    """
    endpoint = f"/order-book/{pair}?limit=5"
    response = requests.get(API_BASE_URL+endpoint)

    print("\n------------------")
    print(f"get_book_order_price() status_code: {response.status_code}\n")
    try:
        return response.json()
    except:
        raise Exception("Unparsable JSON; check response status code")


# DELETE
def cancel_order(pair: str, orderId: str) -> None:
    """
    params: order pair; id of the order to cancel
    performs: cancels an existing order
    returns: None
    """
    endpoint = f"/orders/{pair}/{orderId}"
    response = requests.delete(API_BASE_URL+endpoint, headers=create_default_headers())

    print("\n------------------")
    print(f"cancel_order() status_code: {response.status_code}\n")


# POST
def create_order(order: Order) -> None:
    """
    params: an order object for a specific pair
    function: post a new limit-order request for the given order
    returns: None
    """
    endpoint = f"/orders/{order.get_pair()}"
    body = build_order_body(order)
    response = requests.post(API_BASE_URL+endpoint, headers=create_order_headers(body), data=body)

    print("\n------------------")
    print(f"create_order() status_code: {response.status_code}\n")
    try:
        print(response.json())
    except:
        raise Exception("Unparsable JSON; check response status code")
    finally:
        return response.status_code



def create_stop_limit_order(order: Order) -> None:
    """
    params: an order object for a specific pair
    function: post a new stop-loss/limit-order request for the given order
    returns: None
    """
    endpoint = f"/orders/{order.get_pair()}"
    body = build_order_body_stop_limit(order)
    response = requests.post(API_BASE_URL+endpoint, headers=create_order_headers(body), data=body)

    print("\n------------------")
    print(f"create_stop_limit_order() status_code: {response.status_code}\n")
    try:
        print(response.json())
    except:
        raise Exception("Unparsable JSON; check response status code")



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
    params: None
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


def build_order_body_stop_limit(order: Order, priceRoundingNumber: int = 4) -> str:
    """
    params: an order object for a specific asset for a stop-loss/limit-order
    performs: creates a json formatted string for the body of the HTTP request
    returns: json body as str
    """
    nonce = int(time.time() * 1000) # get current time; *1000 & cast to int because Python is special and uses floats instead of longs...
    amount = round(order.get_available_balance(), 8) # order amount can be at most 8 decimal places long
    hiPrice = round(order.get_hi_price(), priceRoundingNumber) # order prices can be at most 2-4 decimal places long
    loPrice = round(order.get_lo_price(), priceRoundingNumber) # order prices can be at most 2-4 decimal places long
    body = "{" + f"\"action\": \"{order.get_action()}\"," + f"\"amount\": \"{amount}\"," + f"\"price\": \"{hiPrice}\"," + f"\"stopPrice\": \"{loPrice}\"," + "\"condition\": \"<=\"," + f"\"timestamp\": {nonce}," + f"\"type\": \"{order.get_order_type()}\"" + "}"

    return body



# PARSERS
def parse_orders(orders: List[object]) -> str:
    """
    params: a list of orders from a specific asset
    performs: prints order info
    returns: orderId as a str
    """
    sorted_orders = sorted(orders, key=lambda x: x["createdTimestamp"])
    order = orders[-1] # sorted in ascending order, so most recent is the last in the last
    logStr = f"ID: {order['id']}\n" + f"action: {order['action']}\n" + f"type: {order['type']}\n"
    if order["type"] == "STOP_LIMIT":
        logStr += f"Limit-Order Price: {order['price']}\n" + f"Stop-Loss Price: {order['stopPrice']}\n"
    else:
        logStr += f"Limit-Order Price: {order['price']}\n"
    logStr += f"Last updated: {datetime.fromtimestamp(int(order['updatedTimestamp']/1000))}\n"
    logStr += f"Order status: {ORDER_STATUS[str(order['status'])]}"
    if ORDER_STATUS[str(order['status'])] == "In Progress":
        print(order)

    logger.trades(f"\n{logStr}")
    return order["id"]


def parse_balance(balances: List[object], asset: str) -> float:
    """
    params: a list of balances in acct; a specific asset whose balance is of interest
    performs: prints balance info of all current balances
    returns: available balance as a float
    """
    assetBalance =  0.0
    for balance in balances:

        if balance["currency"] == asset:
            print(f"{balance['currency']}: \n\ttotal = {balance['amount']} \n\tavailable = {balance['available']}")
            assetBalance = float(balance["available"])
        elif balance["currency"] == "twd":
            print(f"{balance['currency']}: \n\ttotal = {balance['amount']} \n\tavailable = {balance['available']}")

    return assetBalance


def parse_ticker_price(tickerObj: object) -> float:
    """
    params: a ticker of a specific asset
    performs: prints last price
    returns: lastPrice as a float
    """
    print(f"Last price for {tickerObj['pair']} was: {float(tickerObj['lastPrice']):.2f}TWD")
    print(f"24-delta: {tickerObj['priceChange24hr']}%")
    return float(tickerObj['lastPrice'])


def parse_order_book_orders(orderBook: object, targetPrice: float, amount: float, parseBids: bool) -> float:
    """
    NOTE: bids = buyers; asks = sellers
    params: two lists of orders (bids & asks); the price which to compare the orders to; the amount of an asset which to compare the orders to; whether or not to parse the bids or the asks
    performs: compares the orders' prices and amounts to target values for trade
    returns: the best price to set the order at so that it can be filled ASAP
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
# ------------------------------------
# ------------------------------------
# MAIN
if __name__ == "__main__":
    print("\n------------------")
    print("INITIATING PROGRAM")
    print("------------------")


    """
    ACTUAL BOT
    # boolean flag for whether or not to purchase crypto for a later sale
    shouldPurchase = True
    setStopLimit = False
    originalPurchasePrice = 0.0
    pair = PAIRS["SOL"]

    # create two threads:
    # 1.) To make purchases
    # 2.) To poll price info and sell when limit-order or stop-loss is hit

    # loop where purchase happens
    while True:
        if shouldPurchase:
            try:
                # get amount of funds available for trade
                acctBalances = get_balance()
                twdBalance = parse_balance(acctBalances, "twd")

                # determine trade price and amount
                tmpPrice = parse_ticker_price(get_asset_price(pair)) * 1.02 
                tmpAmount = twdBalance/price

                order_book = get_book_order_price(pair)
                buyPrice = parse_order_book_orders(order_book, tmpPrice, tmpAmount, False)
                buyAmount = twdBalance/buyPrice
 
                # place order
                statusCode = create_order(Order(pair, ACTIONS["buy"], "limit", buyAmount, buyPrice))
                if statusCode != 200:
                    raise Exception(f"Order status code: {statusCode}")
                
                # check if order was filled
                orderFilled = False
                while not orderFilled:
                    pass

                # set purchase price
                originalPurchasePrice = buyPrice
            except Exception as e:
                print(f"Purchase could not be completed: {e}")
            finally:
                shouldPurchase = False
                setStopLimit = True

        # sleep thread until next period to see if a trade should be filled
        time.sleep(60*60*4) 

        # if there are NTD in the acct, that means a successful trade took place over the last period
        acctBalances = get_balance()
        twdBalance = parse_balance(acctBalances, "twd")
        
        if twdBalance > 5: # sometimes there a random few NTD left from "mostly" executed trades
            shouldPurchase = True
            setStopLimit = False
             

    # loop where sale happens
    while True:
        if not shouldPurchase and setStopLimit:
            # check current price
            acctBalances = get_balance()
            assetBalance = parse_balance(acctBalances, "sol")

            order_book = get_book_order_price(pair)
            hiBidPrice = parse_order_book_orders(order_book, originalPurchasePrice * UPSIDE_DELTA, assetBalance, True)
            loAskPrice = parse_order_book_orders(order_book, originalPurchasePrice * DOWNSIDE_DELTA, assetBalance, False)

            # has reached limit-order or stop-loss
            if not hiBidPrice < 0:
                try:
                    statusCode = create_order(Order(pair, ACTIONS["sell"], "limit", assetBalance, hiBidPrice))
                    if statusCode == 200:
                        setStopLimit = False
            elif not loBidPrice < 0:
                try:
                    statusCode = create_order(Order(pair, ACTIONS["sell"], "limit", assetBalance, loBidPrice))
                    if statusCode == 200:
                        setStopLimit = False

        time.sleep(1) # try again in one second
    """


    #TODO: handle raised exceptions
    acctBalances = get_balance()
    assetBalance = parse_balance(acctBalances, "ada")

    pair = PAIRS["ADA"]
    price = parse_ticker_price(get_asset_price(pair))

    mostRecentOrderId = parse_orders(get_orders(pair))

    print("\n------------------")
    print("FINISHING PROGRAM")
    print("------------------")
    """
    HOW TO USE
    ----------
    CANCEL
    cancel_order(pair, mostRecentOrderId)

    BUY
    create_order(Order(pair, ACTIONS["buy"], "limit", assetBalance/price, price))

    SELL
    price *= 1.02
    create_order(Order(pair, ACTIONS["sell"], "limit", assetBalance, price))

    STOP-LIMIT
    hiPrice = price * 1.02
    loPrice = price * 0.98
    create_stop_limit_order(Order(pair, ACTIONS["sell"], "stop_limit", assetBalance, hiPrice, loPrice))

    ORDER BOOK
    order_book = get_book_order_price(pair)
    parse_order_book_orders(order_book, price, assetBalance, True)
    """
