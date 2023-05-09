import common
import time
from .. import trade_bot as tb
from .logger import *
from .order import *
from typing import Tuple

UPSIDE_DELTA = 1.02
DOWNSIDE_DELTA = 0.98

class Strategy():
    def __init__(self, logger: CustomLogger) -> None:
        self.originalPurchasePrice = 0.0
        self.shouldPurchase = True
        self.setStopLimit = False
        self.terminate = False
        self.logger = logger


    def handle_buys(self, pair: str) -> None:
        while not self.terminate:
            acctBalances = tb.get_balance()
            twdBalance = tb.parse_balance(acctBalances, "twd")

            # if there are insufficient funds, don't purchase
            self.shouldPurchase = twdBalance > 100 # buffer in case there is a small residual balance

            if self.shouldPurchase:
                try:
                    self._perform_buy(pair, twdBalance)
                except Exception as e:
                    self.logger.program(f"{e}")

            time.sleep(60*60*2) # Check every two hours 
 
    
    def handle_price_check(self, pair: str) -> None:
        while not self.terminate:
            try:
                # check/log current price
                tb.parse_ticker_price(tb.get_asset_price(pair)) 

                time.sleep(1)
            except Exception as e:
                self.logger.program(f"{e}")
         

    # TODO: Error Handling
    def handle_sales(self, pair: str) -> None:
        while not self.terminate:
            # check if there is a balance of given asset 
            asset = pair[0:pair.find("_")] # parse asset
            acctBalances = tb.get_balance()
            assetBalance = tb.parse_balance(acctBalances, asset)

            # if asset balance is nearly 0, then it implies the sale has succeeded
            # buffer in case there is a small residual balance
            if assetBalance < 0.01:
                self.shouldPurchase = True

            # otherwise, check if should set a stop loss or limit order
            # Bito has a StopLimit endpoint in their API, the problem is, it doesn't actually trigger when it should...
            if not self.shouldPurchase and self.setStopLimit: 
                self._perform_sale(pair, assetBalance)

            time.sleep(1) # Check every second 
 
    # ----------------------
    # PRIVATE HELPER METHODS
    # ----------------------
    def _perform_buy(self, pair: str, twdBalance: float) -> None:
        try:
            # determine trade price and amount
            tmpPrice = tb.parse_ticker_price(tb.get_asset_price(pair)) * 1.01 # 1% > than most recent sale price to make it easier to buy quickly
            tmpAmount = twdBalance/tmpPrice
            orderBook = tb.get_book_order_price(pair)

            # keep querying until appropriate order appears 
            buyPrice, buyAmount = self._find_satisfactory_ask(orderBook, tmpPrice, tmpAmount, twdBalance)

            # place order
            self._place_buy_order(pair, buyAmount, buyPrice)

            # reset relevant global variables
            self.originalPurchasePrice = buyPrice
            self.shouldPurchase = False
            self.setStopLimit = True
        except Exception as e:
            raise e

        # log successful trade
        self.logger.trades(f"originalPurchasePrice = {self.originalPurchasePrice}")


    def _perform_sale(self, pair: str, assetBalance: float) -> None:
            order_book = tb.get_book_order_price(pair)
            hiBidPrice = tb.parse_order_book_orders(order_book, self.originalPurchasePrice * UPSIDE_DELTA, assetBalance, True)
            loAskPrice = tb.parse_order_book_orders(order_book, self.originalPurchasePrice * DOWNSIDE_DELTA, assetBalance, False)

            # place order
            # TODO

            # reset relevant global variables
            self.setStopLimit = False
            self.logger.trades(f"hi = {hiBidPrice} | lo = {loAskPrice}")

            time.sleep(1)


    def _find_satisfactory_ask(self, orderBook: object, tmpPrice: float, tmpAmount: float, twdBalance) -> Tuple[float, float]:
        buyPrice = -1.0
        buyAmount = 0.0
        attempts = 1000

        # attempt to find a satisfactory ask (1000 attempts)
        while True:
            # query order books
            buyPrice = tb.parse_order_book_orders(orderBook, tmpPrice, tmpAmount, False)
            if buyPrice > 0.0:
                buyAmount = twdBalance/buyPrice
                break

            # handle attempts
            attempts -= 1
            if attempts < 1:
                attempts = 10
                self.terminate = True
                raise Exception("Strategy:_find_satisfactory_ask(): Too many attempts to find satisfactory ask failed")

            time.sleep(0.5)
        
        return (buyPrice, buyAmount)


    def _place_buy_order(self, pair: str, buyAmount: float, buyPrice: float) -> None:
        statusCode, orderId = tb.create_order(Order(pair, common.ACTIONS["buy"], "limit", buyAmount, buyPrice))
        if statusCode != 200:
            raise Exception(f"Strategy:_place_buy_order():FAILED ORDER ERROR: Order status code - {statusCode}")
        
        # check if order was filled
        # TODO: perform check to see if there has been a radical move up in price and that's why order isn't filling
        while True:
            mostRecentOrderId, mostRecentOrderStatus = tb.parse_orders(tb.get_orders(pair))
            
            if mostRecentOrderId != orderId:
                self.terminate = True
                raise Exception(f"Strategy:_place_buy_order():ORDER ERROR: mostRecentOrderId ({mostRecentOrderId}) is different from targetOrderId ({orderId}).")

            if mostRecentOrderStatus == common.ORDER_STATUS["2"]: # Completed
                break

            time.sleep(0.5) # try again in one second


