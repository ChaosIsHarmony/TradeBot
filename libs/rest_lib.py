import requests
import time
from datetime import datetime
from ..entities.order import Order
from ..libs import common_lib as comLib
from ..utils.authenticator import *
from ..utils.logger import *
from typing import Any, Dict, List, Tuple

# ------------------------------------
# SETUP
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
    response = requests.get(comLib.API_BASE_URL+endpoint, headers=create_default_headers())


    if response.status_code != 200:
        logger.program(f"rest_lib:get_balance(): status_code: {response.status_code}")
        if comLib.LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_balance() status_code: {response.status_code}\n")

    try:
        return response.json()["data"]
    except Exception as e:
        raise Exception(f"rest_lib:get_balance(): Unparsable JSON; check response status code: {e}")


def get_orders(pair: str) -> List[Dict[str, Any]]:
    """
    params: order pair
    performs: gets list of all orders for specified asset for last 90 days
    returns: list of all orders as dictionaries
    """
    endpoint = f"/orders/all/{pair}"
    response = requests.get(comLib.API_BASE_URL+endpoint, headers=create_default_headers())

    if response.status_code != 200:
        logger.program(f"rest_lib:get_orders(): status_code: {response.status_code}")
        if comLib.LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_orders() status_code: {response.status_code}\n")

    try:
        return response.json()["data"]
    except Exception as e:
        raise Exception(f"rest_lib:get_orders(): Unparsable JSON; check response status code: {e}")

def get_order_by_id(pair: str, orderId: str) -> Dict[str, Any]:
    """
    params: order pair; orderId
    performs: gets a specified order for specified asset for last 90 days
    returns: order as dictionaries
    """
    endpoint = f"/orders/{pair}/{orderId}"
    response = requests.get(comLib.API_BASE_URL+endpoint, headers=create_default_headers())

    if response.status_code != 200:
        logger.program(f"rest_lib:get_order_by_id(): status_code: {response.status_code}")
        if comLib.LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_order_by_id() status_code: {response.status_code}\n")

    try:
        return response.json()
    except Exception as e:
        raise Exception(f"rest_lib:get_order_by_id(): Unparsable JSON; check response status code: {e}")


def get_asset_price(pair: str) -> float:
    """
    params: trading pair (e.g., btc_twd)
    performs: gets most recent price for specified trading pair
    returns: price as a float
    """
    endpoint = f"/tickers/{pair}"
    response = requests.get(comLib.API_BASE_URL+endpoint, headers=create_default_headers())

    if response.status_code != 200:
        logger.program(f"rest_lib:get_asset_price(): status_code: {response.status_code}")
        if comLib.LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_asset_price() status_code: {response.status_code}\n")

    try:
        return response.json()["data"]
    except Exception as e:
        raise Exception(f"rest_lib:get_asset_price(): Unparsable JSON; check response status code: {e}")


def get_book_order_price(pair: str) -> Dict[str, Any]:
    """
    params: trading pair (e.g., btc_twd)
    performs: gets the most recent book order price for specified asset
    returns: bids and asks as a dictionary
    """
    endpoint = f"/order-book/{pair}?limit=1"
    response = requests.get(comLib.API_BASE_URL+endpoint)

    if response.status_code != 200:
        logger.program(f"rest_lib:get_book_order_price(): status_code: {response.status_code}")
        if comLib.LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"get_book_order_price() status_code: {response.status_code}\n")

    try:
        return response.json()
    except Exception as e:
        raise Exception(f"rest_lib:get_book_order_price(): Unparsable JSON; check response status code: {e}")


# DELETE
def cancel_order(pair: str, orderId: str) -> int:
    """
    params: order pair; id of the order to cancel
    performs: cancels an existing order
    returns: response status code
    """
    endpoint = f"/orders/{pair}/{orderId}"
    response = requests.delete(comLib.API_BASE_URL+endpoint, headers=create_default_headers())

    if response.status_code != 200:
        logger.program(f"rest_lib:cancel_order(): status_code: {response.status_code}")
        if comLib.LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"cancel_order() status_code: {response.status_code}\n")

    logger.trades(f"Canceled Order #{orderId}")

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
    response = requests.post(comLib.API_BASE_URL+endpoint, headers=create_order_headers(body), data=body)

    if response.status_code != 200:
        logger.program(f"rest_lib:create_order(): status_code: {response.status_code}")
        if comLib.LOG_TO_CONSOLE:
            print("\n------------------")
            print(f"create_order() status_code: {response.status_code}\n")

    try:
        if comLib.LOG_TO_CONSOLE:
            print("\n------------------")
            print("Created new order:")
            print(response.json())

        result = response.json()
        orderId = result["orderId"]

        logStr = f"\nID: {result['orderId']}\n" 
        logStr += f"action: {result['action']}\n" 
        logStr += f"Price: {result['price']}\n"
        logStr += f"Amount: {result['amount']}\n"
        logStr += f"Created on: {datetime.fromtimestamp(int(result['timestamp']/1000))}\n"
        logger.trades(logStr)
    except Exception as e:
        raise Exception(f"rest_lib:create_order(): Unparsable JSON; check response status code: {e}")

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
