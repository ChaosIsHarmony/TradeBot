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
    
    return { "price": loAskPrice, "amount": amountToPurchase }


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
    print("\tAsset Tickers:")
    print("\t\tADA")
    print("\t\tBTC")
    print("\t\tETH")
    print("\t\tSOL")


if __name__ == "__main__":
    # deactivate extraneous console logging
    comLib.LOG_TO_CONSOLE = False

    try:
        asset = sys.argv[2].lower()
        if sys.argv[1] == "-b": 
            action = "buy"
            orderInfo = check_orders_for_buying(asset)
            if (input("Purchase? (y/n)\n")) == "y":
                place_order(asset + "_twd", "buy", orderInfo["amount"], orderInfo["price"])
        elif sys.argv[1] == "-s": 
            action = "sell"
            orderInfo = check_orders_for_selling(asset)
            if (input("Sell? (y/n)\n")) == "y":
                place_order(asset + "_twd", "sell", orderInfo["amount"], orderInfo["price"])
        else:
            printUsage()
    except:
       printUsage() 
