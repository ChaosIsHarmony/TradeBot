import time
from .. import common
from .. import trade_bot as tb
from .logger import *


PRICE_CHECK_FREQUENCY = 10


class PriceChecker:
    def __init__(self, logger: CustomLogger) -> None:
        self.apiCallsHaveBeenPaused = False
        self.logger = logger
        self.terminate = False

    def handle_price_check(self) -> None:
        prevPrice = 0.0

        while not self.terminate:
            try:
                for pair in common.PAIRS.values():
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
                    time.sleep(common.PAUSE_CHECK_INTERVAL)
                    self.apiCallsHaveBeenPaused = False
                else:
                    time.sleep(PRICE_CHECK_FREQUENCY) 

