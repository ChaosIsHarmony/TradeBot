from datetime import datetime
from ..libs import common_lib as comLib
from typing import List, Tuple

def parse_most_recent_order(orders: List[object]) -> Tuple[str, int]:
    """
    params: a list of orders from a specific asset
    performs: prints order info
    returns: tuple of orderId for most recent order as a str and order status as int
    """
    # sort orders by timestamp
    sorted_orders = sorted(orders, key=lambda x: x["createdTimestamp"])
    order = sorted_orders[-1] # sorted in ascending order, so most recent is the last in the last

    logStr = f"ID: {order['id']}\n" + f"action: {order['action']}\n" + f"type: {order['type']}\n"
    logStr += f"Limit-Order Price: {order['price']}\n" 
    if order["type"] == "STOP_LIMIT":
        logStr += f"Stop-Loss Price: {order['stopPrice']}\n"
    logStr += f"Last updated: {datetime.fromtimestamp(int(order['updatedTimestamp']/1000))}\n"
    logStr += f"Order status: {comLib.ORDER_STATUS[str(order['status'])]}"
    
    if comLib.LOG_TO_CONSOLE and comLib.ORDER_STATUS[str(order["status"])] == "In Progress":
        print("\n------------------")
        print("Parsed Most Recent Order:")
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
    logStr += f"Order status: {comLib.ORDER_STATUS[str(order['status'])]}"
    
    if comLib.LOG_TO_CONSOLE and comLib.ORDER_STATUS[str(order["status"])] == "In Progress":
        print("\n------------------")
        print("Parsed Order Total:")
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
            if comLib.LOG_TO_CONSOLE:
                print("\n------------------")
                print("Parsed Balance:")
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
    """
    if comLib.LOG_TO_CONSOLE:
        print("\n------------------")
        print("Parsed Ticker Price:")
        print(f"Last price for {tickerObj['pair']} was: {float(tickerObj['lastPrice']):.2f}TWD")
        print(f"24-delta: {tickerObj['priceChange24hr']}%")
    """

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
                if comLib.LOG_TO_CONSOLE:
                    print("\n------------------")
                    print("Found appropriate bid:")
                    print(f"price = {bid['price']}")
                return float(bid["price"])
    else:
        for ask in orderBook["asks"]:
            if float(ask["price"]) <= targetPrice and float(ask["amount"]) >= amount: 
                if comLib.LOG_TO_CONSOLE:
                    print("\n------------------")
                    print("Found appropriate ask:")
                    print(f"price = {ask['price']}")
                return float(ask["price"])

    return -1.0
