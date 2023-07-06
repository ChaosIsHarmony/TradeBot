"""
----------
HOW TO RUN
----------
from parent directory:
    $ python3 -m TradeBot.trade_bot
"""
import sys
from typing import Dict
from ..entities.order import *
from ..libs import common_lib as comLib
from ..libs import rest_lib as restLib
from ..libs import parser_lib as parsLib


ASSET_PAIRS = ["ada_twd", "btc_twd", "sol_twd"]


def check_orders_for_buying(asset: str) -> Dict[str, float]:
    availableTWDBalance = parsLib.parse_balance(restLib.get_balance(), "twd")[0]

    orderBook = restLib.get_book_order_price(asset + "_twd")
    loAskPrice, askAmountAvailable = parsLib.parse_order_book_orders_get_lo_ask(orderBook["asks"][0])

    print(f"TWD AVAILABLE: {availableTWDBalance}")
    print()
    print("ASKS (for purchasing)")
    print(f"price: {loAskPrice}")
    print(f"amtAvailable: {askAmountAvailable}")
    amountToPurchase = comLib.round_down(availableTWDBalance/loAskPrice)
    print(f"amtPurchaseableGivenBalanceAvailable: {amountToPurchase}")
    
    return { "price": loAskPrice, "amount": amountToPurchase, "amountAvailable": askAmountAvailable, "availableTWDBalance": availableTWDBalance }


def check_orders_for_selling(asset: str) -> Dict[str, float]:
    availableAssetBalance = parsLib.parse_balance(restLib.get_balance(), asset)[0]
    orderBook = restLib.get_book_order_price(asset + "_twd")
    hiBidPrice, bidAmountAvailable = parsLib.parse_order_book_orders_get_hi_bid(orderBook["bids"][0])

    print(f"ASSET AVAILABLE: {availableAssetBalance}")
    print()
    print("BIDS (for selling)")
    print(f"price: {hiBidPrice}")
    print(f"amtDesired: {bidAmountAvailable}")
    totalSale = comLib.round_down(availableAssetBalance*hiBidPrice)
    print(f"totalSale: {totalSale}")

    return { "price": hiBidPrice, "amount": availableAssetBalance }


def place_order(pair: str, action: str, availableBalance, price) -> None:
    # turn console logging back on to see result of order
    comLib.LOG_TO_CONSOLE = True
    restLib.create_order(Order(pair, comLib.ACTIONS[action], "limit", availableBalance, price))


def printUsage() -> None:
    print("Usage:\tpython3 -m TradeBot.utils.trade_placer [action] [asset ticker]")
    print()
    print("\tActions:")
    print("\t\t-b\tBUY")
    print("\t\t-s\tSELL")
    print("\t\t-p\tPRICES")
    print("\t\t-t\tACTIVE TRADES")
    print("\tAsset Tickers:")
    print("\t\tADA")
    print("\t\tBTC")
    print("\t\tETH")
    print("\t\tLTC")
    print("\t\tMATIC")
    print("\t\tSOL")



def make_purchase_inquiry() -> None:
    orderInfo = check_orders_for_buying(asset)
    if (input("Purchase now? (y/n)\n")) == "y":
        # Sometimes there's not enough available for purchase at a given price
        if orderInfo["amount"] > orderInfo["amountAvailable"]:
            print(f"Only {orderInfo['amountAvailable']} available for purchase, so just buying that amount. For more, place another order.")
            place_order(asset + "_twd", "buy", orderInfo["amountAvailable"], orderInfo["price"])
        else:
            place_order(asset + "_twd", "buy", orderInfo["amount"], orderInfo["price"])
    else:
        if (input("Place a limit buy order? (y/n)\n")) == "y":
            price = float(input("Price: "))
            amount = comLib.round_down(orderInfo["availableTWDBalance"]/price)
            place_order(asset + "_twd", "buy", amount, price)



def make_sale_inquiry() -> None:
    orderInfo = check_orders_for_selling(asset)
    if (input("Sell now? (y/n)\n")) == "y":
        place_order(asset + "_twd", "sell", orderInfo["amount"], orderInfo["price"])
    else:
        if (input("Place a limit sell order? (y/n)\n")) == "y":
            price = float(input("Price: "))
            place_order(asset + "_twd", "sell", orderInfo["amount"], price)



def make_price_inquiry() -> None:
    for pair in ASSET_PAIRS:
        priceInfo = restLib.get_asset_price(pair)
        print(pair)
        print(f"\tLast Price: {priceInfo['lastPrice']}")
        print(f"\tHi 24hr Price: {priceInfo['high24hr']}")
        print(f"\tLo 24hr Price: {priceInfo['low24hr']}")
        print(f"\t24hr Price Delta: {priceInfo['priceChange24hr']}")
        print(f"\t24hr Trade Volume: {priceInfo['volume24hr']}")



def get_status_str(code: int) -> str:
    if code == 0: return "FULLY INCOMPLETE"
    if code == 1: return "PARTIALLY COMPLETED"
    if code == 2: return "COMPLETED"
    return f"Unknown code: {code}"


def make_active_trades_inquiry() -> None:
    for pair in ASSET_PAIRS:
        orderInfo = sorted(restLib.get_orders(pair), key=lambda d: d["updatedTimestamp"])[-1]
        print(pair)
        print(f"\tOrder ID: {orderInfo['id']}")
        print(f"\tType: {orderInfo['action']}")
        print(f"\tStatus: {get_status_str(orderInfo['status'])}")
        print(f"\tPrice: {orderInfo['price']}")
        print(f"\tAvg. Execution Price: {orderInfo['avgExecutionPrice']}")
        print(f"\tTotal: {orderInfo['total']}")
        print(f"\tFee: {orderInfo['fee']}")
        print(f"\tExecuted Amount: {orderInfo['executedAmount']}")
        print(f"\tRemaining Amount: {orderInfo['remainingAmount']}")


if __name__ == "__main__":
    # deactivate extraneous console logging
    comLib.LOG_TO_CONSOLE = False

    try:
        if sys.argv[1] == "-b": 
            asset = sys.argv[2].lower()
            make_purchase_inquiry()
        elif sys.argv[1] == "-s": 
            asset = sys.argv[2].lower()
            make_sale_inquiry()
        elif sys.argv[1] == "-p":
            make_price_inquiry()
        elif sys.argv[1] == "-t":
            make_active_trades_inquiry()
        else:
            printUsage()
    except:
       printUsage() 
