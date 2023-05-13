import logging
# CUSTOM LOG LEVELS
TRADES_LOG_LEVEL = 7
PROGRAM_LOG_LEVEL = 8
PRICE_LOG_LEVEL = 9

class CustomLogger(logging.getLoggerClass()):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        logging.addLevelName(TRADES_LOG_LEVEL, "TRADES")
        logging.addLevelName(PROGRAM_LOG_LEVEL, "PROGRAM")
        logging.addLevelName(PRICE_LOG_LEVEL, "PRICE")


    def trades(self, message, *args, **kws):
        self._log(TRADES_LOG_LEVEL, message, args, **kws)

    def program(self, message, *args, **kws):
        self._log(PROGRAM_LOG_LEVEL, message, args, **kws)

    def price(self, message, *args, **kws):
        self._log(PRICE_LOG_LEVEL, message, args, **kws)



def create_logger() -> CustomLogger:
    """
    HOW TO USE
    logger.trades("This is a trade log message")
    logger.program("This is a program log message")
    logger.price("This is a price log message")
    """
    logger = CustomLogger(__name__)

    tradesHandler = logging.FileHandler("TradeBot/logs/trades.log")
    programHandler = logging.FileHandler("TradeBot/logs/program.log")
    priceHandler = logging.FileHandler("TradeBot/logs/price.log")

    tradesFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    programFormatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    priceFormatter = logging.Formatter("%(message)s")

    tradesHandler.setFormatter(tradesFormatter)
    programHandler.setFormatter(programFormatter)
    priceHandler.setFormatter(priceFormatter)

    tradesHandler.setLevel(TRADES_LOG_LEVEL)
    programHandler.setLevel(PROGRAM_LOG_LEVEL)
    priceHandler.setLevel(PRICE_LOG_LEVEL)

    def program_filter(record):
        return not record.levelno == PROGRAM_LOG_LEVEL

    def price_filter(record):
        return not record.levelno == PRICE_LOG_LEVEL

    tradesHandler.addFilter(program_filter)
    tradesHandler.addFilter(price_filter)
    programHandler.addFilter(price_filter)

    # Add all handlers to logger
    logger.addHandler(tradesHandler)
    logger.addHandler(programHandler)
    logger.addHandler(priceHandler)

    return logger


