import math
import time
from ..libs import common_lib as comLib
from ..libs import parser_lib as parsLib
from ..libs import rest_lib as restLib
from .logger import *


def handle_price_check(logger: CustomLogger) -> None:
    PRICE_CHECK_FREQUENCY = 10
    prevPrice = {pair: 0.0 for pair in comLib.PAIRS.values()}
    apiCallsHaveBeenPaused = False

    while True:
        try:
            for pair in comLib.PAIRS.values():
                # check/log current price
                tickerObj = restLib.get_asset_price(pair)
                newPrice, dailyDelta = parsLib.parse_ticker_price(tickerObj)

                if not math.isclose(newPrice, prevPrice[pair]):
                    if comLib.LOG_TO_CONSOLE:
                        print("\n------------------")
                        print(f"New Price for {pair}:")
                        print(f"{pair},{newPrice},{dailyDelta},{tickerObj['volume24hr']}")
                        
                    prevPrice[pair] = newPrice
                    logger.price(f"{pair},{newPrice},{dailyDelta},{tickerObj['volume24hr']}")

        except Exception as e:
            logger.program(f"Strategy:handle_price_check(): {e}")
            apiCallsHaveBeenPaused = True
        finally:
            if apiCallsHaveBeenPaused:
                time.sleep(comLib.PAUSE_CHECK_INTERVAL)
                apiCallsHaveBeenPaused = False
            else:
                time.sleep(PRICE_CHECK_FREQUENCY) 


if __name__ == "__main__":
    logger = create_logger()
    handle_price_check(logger)
