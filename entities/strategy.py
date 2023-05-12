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
BUY_CHECK_FREQUENCY = 60*60*3  # Check every three hours

PRICE_CHECK_FREQUENCY = 10
SELL_CHECK_FREQUENCY = 5
PAUSE_CHECK_INTERVAL = 60 * 10 # pause API access for 10 minutes

PROFIT_MARGIN_THRESHOLD = 1.1 # every time you make 10%, take profits
PROFIT_MARGIN_AMOUNT = 1 - ((PROFIT_MARGIN_THRESHOLD - 1) / 2) # take half of the increase as profits 

DAILY_DELTA_THRESHOLD_HI = 2.5
DAILY_DELTA_THRESHOLD_LO = -2.5

class Strategy():
    def __init__(self, logger: CustomLogger, principal: float = 1000.0) -> None:
        self.apiCallsHaveBeenPaused = False
        self.principal = principal 
        self.mostRecentSellOrderId = '3277817517'
        self.originalPurchasePrice = 0.0
        self.shouldPurchase = True
        self.setStopLimit = False
        self.terminate = False # for terminating due to errant/unexpected behavior
        self.logger = logger


    def handle_buys(self, pair: str) -> None:
        while not self.terminate:
            try:
                # determine amount of dry powder available
                acctBalances = tb.get_balance()
                twdBalance, _ = tb.parse_balance(acctBalances, "twd")
            
                # if there are insufficient funds, don't purchase
                # either limit order/stop loss have not triggered,
                # or strategy has failed
                # (buffer of 100NTD in case there is a small residual balance)
                self.shouldPurchase = twdBalance > 100 and self.principal > 100 

                if self.shouldPurchase:
                    self._perform_buy(pair, self.principal)

            except Exception as e:
                self.logger.program(f"Strategy:handle_buys(): {e}")
                self.apiCallsHaveBeenPaused = True
            finally:
                if self.apiCallsHaveBeenPaused:
                    time.sleep(PAUSE_CHECK_INTERVAL)
                    self.apiCallsHaveBeenPaused = False
                else:
                    time.sleep(BUY_CHECK_FREQUENCY) 
 
    
    def handle_price_check(self, pair: str) -> None:
        prevPrice = 0.0

        while not self.terminate:
            try:
                # check/log current price
                tickerObj = tb.get_asset_price(pair)
                newPrice, dailyDelta = tb.parse_ticker_price(tickerObj)

                if newPrice != prevPrice:
                    prevPrice = newPrice
                    self.logger.price(f"{pair},{newPrice},{dailyDelta},{tickerObj['volume24hr']}")

            except Exception as e:
                self.logger.program(f"Strategy:handle_price_check(): {e}")
                self.apiCallsHaveBeenPaused = True
            finally:
                if self.apiCallsHaveBeenPaused:
                    time.sleep(PAUSE_CHECK_INTERVAL)
                    self.apiCallsHaveBeenPaused = False
                else:
                    time.sleep(PRICE_CHECK_FREQUENCY) 
 
     

    def handle_sales(self, pair: str) -> None:
        while not self.terminate:
            try:
                # check if there is a balance of given asset 
                asset = pair[:pair.find("_")] # parse asset
                acctBalances = tb.get_balance()
                _, assetBalance = tb.parse_balance(acctBalances, asset)

                # if asset balance is nearly 0, then it implies the sale has succeeded
                # buffer in case there is a small residual balance
                if assetBalance < 0.0001:
                    self._principal_handler(pair)
                    self.shouldPurchase = True

                # otherwise, check if should set a stop loss or limit order
                # Bito has a StopLimit endpoint in their API, the problem is, it doesn't actually trigger when it should...
                if not self.shouldPurchase and self.setStopLimit: 
                    self._perform_sale(pair, assetBalance)

            except Exception as e:
                self.logger.program(f"Strategy:handle_sales(): {e}")
                self.apiCallsHaveBeenPaused = True
            finally:
                if self.apiCallsHaveBeenPaused:
                    time.sleep(PAUSE_CHECK_INTERVAL)
                    self.apiCallsHaveBeenPaused = False
                else:
                    time.sleep(SELL_CHECK_FREQUENCY) 
 
 

    # ----------------------
    # PRIVATE HELPER METHODS
    # ----------------------
    def _perform_buy(self, pair: str, availableBalance: float) -> None:
        try:
            # determine trade price and amount
            tmpPrice, dailyDelta = tb.parse_ticker_price(tb.get_asset_price(pair)) 

            # if dailyDelta to the downside is too negative, then skip buying this period
            if dailyDelta < DAILY_DELTA_THRESHOLD_LO:
                self.logger.trades(f"skipped buy for this period because 24hr delta was too low: {dailyDelta}%")
                return

            tmpPrice *= 1.1 # 1% > than last sale price to make it easier to buy quickly
            tmpAmount = availableBalance/tmpPrice # the max amt we can purchase with available dry powder

            # keep querying until appropriate order appears 
            buyPrice, buyAmount = self._find_satisfactory_ask(pair, tmpPrice, tmpAmount, availableBalance)

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
        try:
            # delay sale if increase is too high (might go higher)
            _, dailyDelta = tb.parse_ticker_price(tb.get_asset_price(pair))
            if dailyDelta > DAILY_DELTA_THRESHOLD_HI:
                self.logger.trades(f"skipped buy for this period because 24hr delta was too high: {dailyDelta}%")
                return

            # get best price for limit-order/stop-loss
            order_book = tb.get_book_order_price(pair)
            hiBidPrice = tb.parse_order_book_orders(order_book, self.originalPurchasePrice * UPSIDE_DELTA, assetBalance, True)
            loAskPrice = tb.parse_order_book_orders(order_book, self.originalPurchasePrice * DOWNSIDE_DELTA, assetBalance, False)

            if hiBidPrice > 0.0 or loAskPrice > 0.0:
                # place limit-order
                if hiBidPrice > 0.0:
                    self.mostRecentSellOrderId, _ = tb.create_order(Order(pair, common.ACTIONS["sell"], "limit", assetBalance, hiBidPrice))
                # place stop-loss
                elif loAskPrice > 0.0:
                    self.mostRecentSellOrderId, _ = tb.create_order(Order(pair, common.ACTIONS["sell"], "limit", assetBalance, loAskPrice))
     
                # reset relevant global variables
                self.setStopLimit = False
        except Exception as e:
            raise e


    def _find_satisfactory_ask(self, pair: str, tmpPrice: float, tmpAmount: float, availableBalance) -> Tuple[float, float]:
        buyPrice = -1.0
        buyAmount = 0.0
        attempts = 10000

        # attempt to find a satisfactory ask (10000 attempts before thread raises an exception and terminates)
        while True:
            # query order books
            buyPrice = tb.parse_order_book_orders(tb.get_book_order_price(pair), tmpPrice, tmpAmount, False)
            if buyPrice > 0.0:
                buyAmount = availableBalance/buyPrice
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


    def _principal_handler(self, pair: str) -> None:
        # get most recent order for pair price
        saleTotal, orderStatus = tb.parse_order_total(tb.get_order_by_id(pair, self.mostRecentSellOrderId))

        # check to make sure the order has been filled 
        if not orderStatus == 2: # not Completed
            raise Exception(f"Strategy:_principal_handler():ORDER ERROR: attempted to readjust principal on an incomplete order: mostRecentSellOrderId = {self.mostRecentSellOrderId}.")

        # if principal has reached threshold, reset it to the reflect profit taking
        if self.principal * PROFIT_MARGIN_THRESHOLD >= saleTotal:
            self.principal = saleTotal * PROFIT_MARGIN_AMOUNT
        else:
            self.principal = saleTotal
