"""
----------
HOW TO RUN
----------
from parent directory:
    $ python3 -m TradeBot.trade_bot
"""
import threading
from ..utils.price_checker import *
from ..strategies.short_term_strategy import *


# ------------------------------------
# MAIN
# ------------------------------------
if __name__ == "__main__":
    print("\n------------------")
    print("INITIATING PROGRAM")
    print("------------------")

    pair = comLib.PAIRS["ETH"]

    print("\n------------------")
    print("LOADING STRATEGY")

<<<<<<< HEAD
    strategy = ShortTermStrategy(upsideDelta=0.005,downsideDelta=0.02,buyFrequency=3)
=======
    strategy = ShortTermStrategy(principal=1990.0)
>>>>>>> 1cbbede4687a191c598e090728635e3039fa0536

    print("\n------------------")
    print("CREATING THREADS")

    buyThread = threading.Thread(target=strategy.handle_buys, args=[pair])
    sellThread = threading.Thread(target=strategy.handle_sales, args=[pair])

    print("\n------------------")
    print("EXECUTING THREADS")

    buyThread.start()
    sellThread.start()

    buyThread.join()
    sellThread.join()

    print("\n------------------")
    print("TERMINATING PROGRAM")
    print("------------------") 
