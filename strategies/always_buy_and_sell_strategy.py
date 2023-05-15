"""
LENGTH:     Short-term
CONDITIONS: 
    - Sell when position has changed +/- 2%
    - Repeat until principal reaches below threshold
    - Take 5% profits when position has increased by 10%
    - Always BUY at the beginning of the period and SELL at the end of the period
"""
import time
from ..libs import common_lib as comLib
from ..libs import parser_lib as parsLib
from ..libs import rest_lib as restLib
from ..utils.logger import *
from ..entities.order import *
from typing import Tuple


# These three values are the heart of the strategy:
# UPSIDE_DELTA determines when to sell for a profit
UPSIDE_DELTA = 1.02
# DOWNSIDE_DELTA determines when to sell for a stop loss
DOWNSIDE_DELTA = 0.98
# BUY_CHECK_FREQUENCY determines the period of the trade (or at least when next to check for buying opportunity)
BUY_CHECK_FREQUENCY = 60*60*4  # Check every three hours

SELL_CHECK_FREQUENCY = 5

PROFIT_MARGIN_THRESHOLD = 1.1 # every time you make 10%, take profits
PROFIT_MARGIN_AMOUNT = 1 - ((PROFIT_MARGIN_THRESHOLD - 1) / 2) # take half of the increase as profits 

class AlwaysBuyAndSellStrategy():
    def __init__(self, principal: float = 1000.0) -> None:
        self.apiCallsHaveBeenPaused = False
        self.principal = principal 
        self.mostRecentSellOrderId = ""
        self.originalPurchasePrice = 0.0
        self.shouldPurchase = True
        self.setStopLimit = False
        self.terminate = False # for terminating due to errant/unexpected behavior
        self.logger = create_logger()


    def handle_buys(self, pair: str) -> None:
        while not self.terminate:
            try:
                # determine amount of dry powder available
                acctBalances = restLib.get_balance()
                twdBalance, _ = parsLib.parse_balance(acctBalances, "twd")
            
                # if there are insufficient funds, don't purchase
                # either limit order/stop loss have not triggered,
                # or strategy has failed
                # (buffer of 100NTD in case there is a small residual balance)
                self.shouldPurchase = twdBalance > 100 and self.principal > 100 

                # if limit order hasn't triggered, force a sale
                if not self.shouldPurchase and self.principal > 100:
                    self._force_sale(pair)
                if self.shouldPurchase:
                    self._perform_buy(pair, self.principal)

            except Exception as e:
                self.logger.program(f"AlwaysBuyAndSellStrategy:handle_buys(): {e}")
                self.apiCallsHaveBeenPaused = True
            finally:
                if self.apiCallsHaveBeenPaused:
                    time.sleep(comLib.PAUSE_CHECK_INTERVAL)
                    self.apiCallsHaveBeenPaused = False
                else:
                    time.sleep(BUY_CHECK_FREQUENCY) 
 
    
    def handle_sales(self, pair: str) -> None:
        while not self.terminate:
            try:
                if self.setStopLimit:
                    # check if there is a balance of given asset 
                    asset = pair[:pair.find("_")] # parse asset
                    acctBalances = restLib.get_balance()
                    _, assetBalance = parsLib.parse_balance(acctBalances, asset)

                    # if asset balance is nearly 0, then it implies the sale has succeeded
                    # buffer in case there is a small residual balance
                    if assetBalance < 0.0001:
                        self._principal_handler(pair)
                        self.shouldPurchase = True

                    # otherwise, check if should set a stop loss or limit order
                    # Bito has a StopLimit endpoint in their API, the problem is, it doesn't actually trigger when it should...
                    if not self.shouldPurchase: 
                        self._perform_sale(pair, assetBalance)

            except Exception as e:
                self.logger.program(f"AlwaysBuyAndSellStrategy:handle_sales(): {e}")
                self.apiCallsHaveBeenPaused = True
            finally:
                if self.apiCallsHaveBeenPaused:
                    time.sleep(comLib.PAUSE_CHECK_INTERVAL)
                    self.apiCallsHaveBeenPaused = False
                else:
                    time.sleep(SELL_CHECK_FREQUENCY) 
 
 

    # ----------------------
    # PRIVATE HELPER METHODS
    # ----------------------
    def _perform_buy(self, pair: str, availableBalance: float) -> None:
        try:
            # determine trade price and amount
            tmpPrice, _ = parsLib.parse_ticker_price(restLib.get_asset_price(pair)) 

            tmpPrice *= 1.1 # 1% > than last sale price to make it easier to buy quickly
            tmpAmount = availableBalance/tmpPrice # the max amt we can purchase with available dry powder

            # keep querying until appropriate order appears 
            buyPrice, buyAmount = self._find_satisfactory_ask(pair, tmpPrice, tmpAmount, availableBalance)
            # if failed to find appropriate ask, wait and then try again 
            if buyPrice < 0.0:
                time.sleep(comLib.PAUSE_CHECK_INTERVAL)
                self._perform_buy(pair, availableBalance)

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
                self.logger.program(f"AlwaysBuyAndSellStrategy:_perform_buy(): Could not purchase {pair} @ {buyPrice} NTD for {buyAmount} coins.")
        except Exception as e:
            raise e

        
    def _perform_sale(self, pair: str, assetBalance: float) -> None:
        try:
            # get best price for limit-order/stop-loss
            order_book = restLib.get_book_order_price(pair)
            hiBidPrice = parsLib.parse_order_book_orders(order_book, self.originalPurchasePrice * UPSIDE_DELTA, assetBalance, True)
            loBidPrice = parsLib.parse_order_book_orders(order_book, self.originalPurchasePrice * DOWNSIDE_DELTA, assetBalance, True)

            if hiBidPrice > 0.0 or loBidPrice > 0.0:
                # place limit-order
                if hiBidPrice > 0.0:
                    self.mostRecentSellOrderId, _ = restLib.create_order(Order(pair, comLib.ACTIONS["sell"], "limit", assetBalance, hiBidPrice))
                # place stop-loss
                elif loBidPrice > 0.0:
                    self.mostRecentSellOrderId, _ = restLib.create_order(Order(pair, comLib.ACTIONS["sell"], "limit", assetBalance, loBidPrice))
     
                # reset relevant global variables
                self.setStopLimit = False
        except Exception as e:
            raise e


    def _find_satisfactory_ask(self, pair: str, tmpPrice: float, tmpAmount: float, availableBalance) -> Tuple[float, float]:
        buyPrice = -1.0
        buyAmount = 0.0
        attempts = 100

        # attempt to find a satisfactory ask (10000 attempts before thread raises an exception and terminates)
        while True:
            # query order books
            buyPrice = parsLib.parse_order_book_orders(restLib.get_book_order_price(pair), tmpPrice, tmpAmount, False)
            if buyPrice > 0.0:
                buyAmount = availableBalance/buyPrice
                break

            # handle attempts
            attempts -= 1
            if attempts < 1:
                self.logger.program("AlwaysBuyAndSellStrategy:_find_satisfactory_ask(): Too many attempts to find satisfactory ask.")
                break

            time.sleep(0.25) # wait a bit and check again to see if there are new orders 
        
        return (buyPrice, buyAmount)


    def _place_buy_order(self, pair: str, buyAmount: float, buyPrice: float) -> bool:
        statusCode, orderId = restLib.create_order(Order(pair, comLib.ACTIONS["buy"], "limit", buyAmount, buyPrice))
        if statusCode != 200:
            raise Exception(f"AlwaysBuyAndSellStrategy:_place_buy_order():FAILED ORDER ERROR: Order status code - {statusCode}")
        
        # check if order was filled
        attempts = 1000
        while True:
            mostRecentOrderId, mostRecentOrderStatus = parsLib.parse_most_recent_order(restLib.get_orders(pair))
            
            if mostRecentOrderId != orderId:
                self.terminate = True
                raise Exception(f"AlwaysBuyAndSellStrategy:_place_buy_order():ORDER ERROR: mostRecentOrderId ({mostRecentOrderId}) is different from targetOrderId ({orderId}).")

            if mostRecentOrderStatus == 2: # Completed
                return True

            attempts -= 1
            if attempts < 1:
                return False

            time.sleep(0.5) # try again after waiting


    def _principal_handler(self, pair: str) -> None:
        # get most recent order for pair price
        saleTotal, orderStatus = parsLib.parse_order_total(restLib.get_order_by_id(pair, self.mostRecentSellOrderId))

        # check to make sure the order has been filled 
        if not orderStatus == 2: # not Completed
            raise Exception(f"AlwaysBuyAndSellStrategy:_principal_handler():ORDER ERROR: attempted to readjust principal on an incomplete order: mostRecentSellOrderId = {self.mostRecentSellOrderId}.")

        # if principal has reached threshold, reset it to the reflect profit taking
        if self.principal * PROFIT_MARGIN_THRESHOLD >= saleTotal:
            self.principal = saleTotal * PROFIT_MARGIN_AMOUNT
        else:
            self.principal = saleTotal


    def _force_sale(self, pair: str) -> None:
        # reset relevant global variables
        self.setStopLimit = False

        while True:
            try:
                # check if there is a balance of given asset 
                asset = pair[:pair.find("_")] # parse asset
                acctBalances = restLib.get_balance()
                _, assetBalance = parsLib.parse_balance(acctBalances, asset)

                # otherwise, check if should set a stop loss or limit order
                # Bito has a StopLimit endpoint in their API, the problem is, it doesn't actually trigger when it should...
                if not self.shouldPurchase: 
                    self._perform_sale(pair, assetBalance)

                # determine trade price and amount
                tmpPrice, _ = parsLib.parse_ticker_price(restLib.get_asset_price(pair)) 
 
                # get best price for limit-order/stop-loss
                order_book = restLib.get_book_order_price(pair)
                loBidPrice = parsLib.parse_order_book_orders(order_book, tmpPrice * 0.99, assetBalance, True)

                # place limit-order
                if loBidPrice > 0.0:
                    self.mostRecentSellOrderId, _ = restLib.create_order(Order(pair, comLib.ACTIONS["sell"], "limit", assetBalance, loBidPrice))
                   break

            except Exception as e:
                self.logger.program(f"AlwaysBuyAndSellStrategy:_force_sale(): {e}")
                self.apiCallsHaveBeenPaused = True
            finally:
                if self.apiCallsHaveBeenPaused:
                    time.sleep(comLib.PAUSE_CHECK_INTERVAL)
                    self.apiCallsHaveBeenPaused = False
