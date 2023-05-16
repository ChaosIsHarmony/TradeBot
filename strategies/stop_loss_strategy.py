"""
LENGTH:     Medium-term
CONDITIONS:  
    - This strategy involves buying and holding until the position falls 15% from its peak value
"""
import time
from ..entities.order import *
from ..libs import common_lib as comLib
from ..libs import parser_lib as parsLib
from ..libs import rest_lib as restLib
from ..utils.logger import *
from typing import Tuple

STOP_LOSS = 0.85 # 15% stop loss

BUY_CHECK_FREQUENCY = 60 * 5 # wait five minutes
SELL_CHECK_FREQUENCY = 5

class StopLossStrategy():
    def __init__(self) -> None:
        self.apiCallsHaveBeenPaused = False
        self.mostRecentSellOrderId = ""
        self.peakPrice = 0.0
        self.setStopLimit = False
        self.terminate = False # for terminating due to errant/unexpected behavior
        self.logger = create_logger() 


    def handle_buys(self, pair: str) -> None:
        """
        Executed only once at strategy start
        """
        try:
            # determine amount of dry powder available
            acctBalances = restLib.get_balance()
            twdBalance, _ = parsLib.parse_balance(acctBalances, "twd")
        
            # if there are insufficient funds, don't purchase
            # either limit order/stop loss have not triggered,
            # or strategy has failed
            # (buffer of 100NTD in case there is a small residual balance)
            shouldPurchase = twdBalance > 100 

            if shouldPurchase:
                self._perform_buy(pair, twdBalance)

        except Exception as e:
            self.logger.program(f"StopLossStrategy:handle_buys(): {e}")
 
    
    def handle_sales(self, pair: str) -> None:
        while not self.terminate:
            try:
                # check if there is a balance of given asset 
                asset = pair[:pair.find("_")] # parse asset
                acctBalances = restLib.get_balance()
                _, assetBalance = parsLib.parse_balance(acctBalances, asset)

                if assetBalance < 0.0001:
                    # check if should set a stop loss
                    if self.setStopLimit:
                        # Bito has a StopLimit endpoint in their API, the problem is, it doesn't actually trigger when it should...
                        self._perform_sale(pair, assetBalance)
                    # check to see if sale has succeeded
                else:
                    totalSale, orderStatus  = parsLib.parse_order_total(restLib.get_order_by_id(pair, self.mostRecentSellOrderId))
                    if comLib.ORDER_STATUS[str(orderStatus)] == "Completed":
                        self.logger.trades(f"SELL,{pair},{totalSale}")

            except Exception as e:
                self.logger.program(f"StopLossStrategy:handle_sales(): {e}")
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

            tmpPrice *= 1.01 # 1% > than last sale price to make it easier to buy quickly
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
                self.peakPrice = buyPrice
                self.setStopLimit = True
                # log successful trade
                self.logger.trades(f"BUY,{pair},{buyPrice},{buyAmount}")
            else:
                self.logger.program(f"StopLossStrategy:_perform_buy(): Could not purchase {pair} @ {buyPrice} NTD for {buyAmount} coins.")
        except Exception as e:
            raise e

        
    def _perform_sale(self, pair: str, assetBalance: float) -> None:
        try:
            # determin latest price
            lastPrice, _ = parsLib.parse_ticker_price(restLib.get_asset_price(pair)) 
            if lastPrice > self.peakPrice:
                self.peakPrice = lastPrice

            # get best price for stop-loss
            order_book = restLib.get_book_order_price(pair)
            hiBidPrice = parsLib.parse_order_book_orders(order_book, self.peakPrice * STOP_LOSS, assetBalance, True)

            # place stop-loss
            if hiBidPrice > 0.0:
                self.mostRecentSellOrderId, _ = restLib.create_order(Order(pair, comLib.ACTIONS["sell"], "limit", assetBalance, hiBidPrice))
     
                # reset relevant global variables
                self.setStopLimit = False
        except Exception as e:
            raise e


    def _find_satisfactory_ask(self, pair: str, tmpPrice: float, tmpAmount: float, availableBalance) -> Tuple[float, float]:
        buyPrice = -1.0
        buyAmount = -1.0
        attempts = 100

        # attempt to find a satisfactory ask (100 attempts before thread raises an exception and terminates)
        while True:
            # query order books
            buyPrice = parsLib.parse_order_book_orders(restLib.get_book_order_price(pair), tmpPrice, tmpAmount, False)
            if buyPrice > 0.0:
                buyAmount = availableBalance/buyPrice
                break

            # handle attempts
            attempts -= 1
            if attempts < 1:
                self.logger.program("StopLossStrategy:_find_satisfactory_ask(): Too many attempts to find satisfactory ask.")
                break

            time.sleep(0.25) # wait a bit and check again to see if there are new orders 
        
        return (buyPrice, buyAmount)


    def _place_buy_order(self, pair: str, buyAmount: float, buyPrice: float) -> bool:
        statusCode, orderId = restLib.create_order(Order(pair, comLib.ACTIONS["buy"], "limit", buyAmount, buyPrice))
        if statusCode != 200:
            raise Exception(f"StopLossStrategy:_place_buy_order():FAILED ORDER ERROR: Order status code - {statusCode}")
        
        # check if order was filled
        attempts = 100
        while True:
            mostRecentOrderId, mostRecentOrderStatus = parsLib.parse_most_recent_order(restLib.get_orders(pair))
            
            if mostRecentOrderId != orderId:
                self.terminate = True
                raise Exception(f"StopLossStrategy:_place_buy_order():ORDER ERROR: mostRecentOrderId ({mostRecentOrderId}) is different from targetOrderId ({orderId}).")

            if comLib.ORDER_STATUS[str(mostRecentOrderStatus)] == "Completed":
                return True

            attempts -= 1
            if attempts < 1:
                return False

            time.sleep(0.5) # try again after waiting
