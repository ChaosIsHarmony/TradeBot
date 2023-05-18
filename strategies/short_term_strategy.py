"""
LENGTH:     Short-term
CONDITIONS: 
    - Sell when position has changed +/- 2%
    - Repeat until principal reaches below threshold
    - Take 5% profits when position has increased by 10%
    - Delay purchase or sale while the daily delta is > 2.5% (FOR SELL) or < -2.5% (FOR BUY) 
"""
import time
from ..entities.order import *
from ..libs import common_lib as comLib
from ..libs import parser_lib as parsLib
from ..libs import rest_lib as restLib
from ..utils.logger import *
from typing import Tuple


class ShortTermStrategy():
    def __init__(self, upsideDelta: float, downsideDelta: float, buyFrequency: int, profitMarginThreshold: float = 0.1, dailyDeltaThresholdLo: float = -0.025) -> None:
        """
        params: 
            - upsideDelta is the percentage of when to sell for a profit
            - downsideDelta is the percentage of when to sell for a stop loss
            - buyFrequency is the interval of hours between checking for buying opportunities
            - profitMarginThreshold is when to take profits (default after an increase of 10% in principal)
            - dailyDeltaThresholdLo signals when to delay a purchase
        """
        # basic setup
        self.apiCallsHaveBeenPaused = False
        self.logger = create_logger()
        self.mostRecentSellOrderId = ""
        self.originalPurchasePrice = 0.0
        self.principal = self._get_available_balance()
        self.shouldPurchase = True
        self.setStopLimit = False
        self.terminate = False # for terminating due to errant/unexpected behavior

        # These three values are the heart of the strategy:
        # determines multiple of principal when to sell for a profit
        self.upsideDelta = 1 + upsideDelta
        # determines multiple of principal when to sell for a stop loss
        self.downsideDelta = 1 - downsideDelta
        # determines the period of the trade (or at least when next to check for buying opportunity)
        self.buyFrequency = 60*60*buyFrequency  # Check every three hours


        self.profitMarginThreshold = 1 + profitMarginThreshold # every time you make 10%, take profits
        self.profitMarginAmount = 1 - ((self.profitMarginThreshold - 1) / 2) # take half of the increase as profits 
        # Avoid purchase if price has dropped by more than threshold in 24hr period (might go lower) 
        self.dailyDeltaThresholdLo = dailyDeltaThresholdLo * 100 # Bito gives it back in percent (%)


    def handle_buys(self, pair: str) -> None:
        while not self.terminate:
            try:
                # determine amount of dry powder available
                twdBalance = self._get_available_balance()
            
                # if there are insufficient funds, don't purchase
                # either limit order/stop loss have not triggered,
                # or strategy has failed
                # (buffer of 100NTD in case there is a small residual balance)
                self.shouldPurchase = twdBalance > 100 and self.principal > 100 

                if self.shouldPurchase:
                    self._perform_buy(pair, self.principal)

            except Exception as e:
                self.logger.program(f"ShortTermStrategy:handle_buys(): {e}")
                self.apiCallsHaveBeenPaused = True
            finally:
                if self.apiCallsHaveBeenPaused:
                    time.sleep(comLib.PAUSE_CHECK_INTERVAL)
                    self.apiCallsHaveBeenPaused = False
                else:
                    time.sleep(self.buyFrequency) 
 
    
    def handle_sales(self, pair: str) -> None:
        while not self.terminate:
            try:
                if not self.shouldPurchase:
                    # check if there is a balance of given asset
                    # uses totalBalance instead of availableBalance because when a sell order is placed, the availableBalance is less than the totalBalance until the order has been filled
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
                    if self.setStopLimit: 
                        self._perform_sale(pair, assetBalance)

            except Exception as e:
                self.logger.program(f"ShortTermStrategy:handle_sales(): {e}")
                self.apiCallsHaveBeenPaused = True
            finally:
                if self.apiCallsHaveBeenPaused:
                    time.sleep(comLib.PAUSE_CHECK_INTERVAL)
                    self.apiCallsHaveBeenPaused = False
                else:
                    time.sleep(comLib.SELL_CHECK_FREQUENCY) 
 
 

    # ----------------------
    # PRIVATE HELPER METHODS
    # ----------------------
    def _perform_buy(self, pair: str, availableBalance: float) -> None:
        try:
            # determine trade price and amount
            tmpPrice, dailyDelta = parsLib.parse_ticker_price(restLib.get_asset_price(pair)) 

            # if dailyDelta to the downside is too negative, then skip buying this period
            if dailyDelta < self.dailyDeltaThresholdLo:
                self.logger.trades(f"skipped buy for this period because 24hr delta was too low: {dailyDelta}%")
                return

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
                self.logger.program(f"ShortTermStrategy:_perform_buy(): Could not purchase {pair} @ {buyPrice} NTD for {buyAmount} coins.")
        except Exception as e:
            raise e

        
    def _perform_sale(self, pair: str, assetBalance: float) -> None:
        try:
            # get best price for limit-order/stop-loss
            order_book = restLib.get_book_order_price(pair)
            hiBidPrice = parsLib.parse_order_book_orders(order_book, self.originalPurchasePrice * self.upsideDelta, assetBalance, True)
            loBidPrice = parsLib.parse_order_book_orders(order_book, self.originalPurchasePrice * self.downsideDelta, assetBalance, True)

            # place limit-order
            if hiBidPrice > 0.0:
                self.mostRecentSellOrderId, _ = restLib.create_order(Order(pair, comLib.ACTIONS["sell"], "limit", assetBalance, hiBidPrice))
                # reset relevant global variables
                self.setStopLimit = False
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
                self.logger.program("ShortTermStrategy:_find_satisfactory_ask(): Too many attempts to find satisfactory ask.")
                break

            time.sleep(0.25) # wait a bit and check again to see if there are new orders 
        
        return (buyPrice, buyAmount)


    def _place_buy_order(self, pair: str, buyAmount: float, buyPrice: float) -> bool:
        statusCode, orderId = restLib.create_order(Order(pair, comLib.ACTIONS["buy"], "limit", buyAmount, buyPrice))
        if statusCode != 200:
            raise Exception(f"ShortTermStrategy:_place_buy_order():FAILED ORDER ERROR: Order status code - {statusCode}")
        
        # check if order was filled
        attempts = 1000
        while True:
            mostRecentOrderId, mostRecentOrderStatus = parsLib.parse_most_recent_order(restLib.get_orders(pair))
            
            if mostRecentOrderId != orderId:
                self.terminate = True
                raise Exception(f"ShortTermStrategy:_place_buy_order():ORDER ERROR: mostRecentOrderId ({mostRecentOrderId}) is different from targetOrderId ({orderId}).")

            if mostRecentOrderStatus == 2: # Completed
                return True

            attempts -= 1
            if attempts < 1:
                return False

            time.sleep(0.5) # try again after waiting


    def _principal_handler(self, pair: str) -> None:
        """
        params: asset pair as a str
        performs: 
            - check to see if order has completed
            - takes profits if has reached profitMarginThreshold
            - readjusts principal to reflect how much is available for trades
        """
        # get most recent order for pair price
        saleTotal, orderStatus = parsLib.parse_order_total(restLib.get_order_by_id(pair, self.mostRecentSellOrderId))

        # check to make sure the order has been filled 
        if not orderStatus == 2: # not Completed
            raise Exception(f"ShortTermStrategy:_principal_handler():ORDER ERROR: attempted to readjust principal on an incomplete order: mostRecentSellOrderId = {self.mostRecentSellOrderId}.")

        # if principal has reached threshold, reset it to the reflect profit taking
        if self.principal * self.profitMarginThreshold >= saleTotal:
            self.principal = saleTotal * self.profitMarginAmount
        else:
            self.principal = saleTotal


    def _get_available_balance(self) -> float:
        """
        returns: avaialble dry powder for purchases
        """
        acctBalances = restLib.get_balance()
        twdBalance, _ = parsLib.parse_balance(acctBalances, "twd")
        
        return twdBalance
