import time
from .. import common
from .. import trade_bot as tb
from .logger import *
from .order import *
from typing import Tuple


# These three values are the heart of the strategy:
# UPSIDE_DELTA determines when to sell for a profit
UPSIDE_DELTA = 1.02
# DOWNSIDE_DELTA determines when to sell for a stop loss
DOWNSIDE_DELTA = 0.98
# BUY_CHECK_FREQUENCY determines the period of the trade (or at least when next to check for buying opportunity)
BUY_CHECK_FREQUENCY = 60*60*2  # Check every two hours

PRICE_CHECK_FREQUENCY = 1
SELL_CHECK_FREQUENCY = 1

class Strategy():
    def __init__(self, logger: CustomLogger) -> None:
        self.originalPurchasePrice = 0.0
        self.shouldPurchase = True
        self.setStopLimit = False
        self.terminate = False # for terminating due to errant/unexpected behavior
        self.logger = logger


    def handle_buys(self, pair: str) -> None:
        while not self.terminate:
            # determine amount of dry powder available
            acctBalances = tb.get_balance()
            twdBalance = tb.parse_balance(acctBalances, "twd")

            # if there are insufficient funds, don't purchase
            # either limit order/stop loss have not triggered,
            # or strategy has failed
            self.shouldPurchase = twdBalance > 100 # buffer in case there is a small residual balance

            if self.shouldPurchase:
                try:
                    self._perform_buy(pair, twdBalance)
                except Exception as e:
                    self.logger.program(f"{e}")

            time.sleep(BUY_CHECK_FREQUENCY) 
 
    
    def handle_price_check(self, pair: str) -> None:
        prevPrice = 0.0

        while not self.terminate:
            try:
                # check/log current price
                tickerObj = tb.get_asset_price(pair)
                newPrice = tb.parse_ticker_price(tickerObj)

                if newPrice != prevPrice:
                    prevPrice = newPrice
                    self.logger.price(f"{tickerObj['pair']},{tickerObj['lastPrice']},{tickerObj['priceChange24hr']},{tickerObj['volume24hr']}")

                time.sleep(PRICE_CHECK_FREQUENCY)
            except Exception as e:
                self.logger.program(f"{e}")
         

    # TODO: Error Handling
    def handle_sales(self, pair: str) -> None:
        while not self.terminate:
            # check if there is a balance of given asset 
            asset = pair[:pair.find("_")] # parse asset
            acctBalances = tb.get_balance()
            assetBalance = tb.parse_balance(acctBalances, asset)

            # if asset balance is nearly 0, then it implies the sale has succeeded
            # buffer in case there is a small residual balance
            if assetBalance < 0.0001:
                self.shouldPurchase = True

            # otherwise, check if should set a stop loss or limit order
            # Bito has a StopLimit endpoint in their API, the problem is, it doesn't actually trigger when it should...
            if not self.shouldPurchase and self.setStopLimit: 
                self._perform_sale(pair, assetBalance)

            time.sleep(SELL_CHECK_FREQUENCY) 
 
    # ----------------------
    # PRIVATE HELPER METHODS
    # ----------------------
    def _perform_buy(self, pair: str, twdBalance: float) -> None:
        try:
            # determine trade price and amount
            tmpPrice = tb.parse_ticker_price(tb.get_asset_price(pair)) * 1.01 # 1% > than last sale price to make it easier to buy quickly
            tmpAmount = twdBalance/tmpPrice # the max amt we can purchase with available dry powder

            # keep querying until appropriate order appears 
            buyPrice, buyAmount = self._find_satisfactory_ask(pair, tmpPrice, tmpAmount, twdBalance)

            # place order
            purchaseSuccessful = self._place_buy_order(pair, buyAmount, buyPrice)

            # reset relevant global variables
            if purchaseSuccessful:
                self.originalPurchasePrice = buyPrice
                self.shouldPurchase = False
                self.setStopLimit = True
                # log successful trade
                self.logger.trades(f"originalPurchasePrice = {self.originalPurchasePrice}")
            else:
                self.terminate = True
                self.logger.program(f"Strategy:_perform_buy(): Could not purchase {pair} @ {buyPrice} NTD for {buyAmount} coins.")
        except Exception as e:
            raise e

        
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


    def _find_satisfactory_ask(self, pair: str, tmpPrice: float, tmpAmount: float, twdBalance) -> Tuple[float, float]:
        buyPrice = -1.0
        buyAmount = 0.0
        attempts = 10000

        # attempt to find a satisfactory ask (10000 attempts before thread raises an exception and terminates)
        while True:
            # query order books
            buyPrice = tb.parse_order_book_orders(tb.get_book_order_price(pair), tmpPrice, tmpAmount, False)
            if buyPrice > 0.0:
                buyAmount = twdBalance/buyPrice
                break

            # handle attempts
            attempts -= 1
            if attempts < 1:
                self.terminate = True
                raise Exception("Strategy:_find_satisfactory_ask(): Too many attempts to find satisfactory ask.")

            time.sleep(0.25) # wait a bit and check again to see if there are new orders 
        
        return (buyPrice, buyAmount)


    def _place_buy_order(self, pair: str, buyAmount: float, buyPrice: float) -> bool:
        statusCode, orderId = tb.create_order(Order(pair, common.ACTIONS["buy"], "limit", buyAmount, buyPrice))
        if statusCode != 200:
            raise Exception(f"Strategy:_place_buy_order():FAILED ORDER ERROR: Order status code - {statusCode}")
        
        # check if order was filled
        attempts = 1000
        while True:
            mostRecentOrderId, mostRecentOrderStatus = tb.parse_orders(tb.get_orders(pair))
            
            if mostRecentOrderId != orderId:
                self.terminate = True
                raise Exception(f"Strategy:_place_buy_order():ORDER ERROR: mostRecentOrderId ({mostRecentOrderId}) is different from targetOrderId ({orderId}).")

            if mostRecentOrderStatus == 2: # Completed
                return True

            attempts -= 1
            if attempts < 1:
                return False

            time.sleep(0.5) # try again after waiting
