import asyncio
import json
import websockets
from .logger import *


class PriceChecker:
    def __init__(self, logger: CustomLogger) -> None:
        self.logger = logger
        asyncio.get_event_loop().run_until_complete(self._handle_price_check())
        asyncio.get_event_loop().run_forever()


    async def _handle_price_check(self) -> None:
        try:
            async with websockets.connect("wss://stream.bitopro.com:9443/ws/v1/pub/tickers?pairs=BTC_TWD") as websocket:
                self._parse_and_log_ticker_response(await websocket.recv())
            async with websockets.connect("wss://stream.bitopro.com:9443/ws/v1/pub/tickers?pairs=ETH_TWD") as websocket:
                self._parse_and_log_ticker_response(await websocket.recv())
            async with websockets.connect("wss://stream.bitopro.com:9443/ws/v1/pub/tickers?pairs=SOL_TWD") as websocket:
                self._parse_and_log_ticker_response(await websocket.recv())
            async with websockets.connect("wss://stream.bitopro.com:9443/ws/v1/pub/tickers?pairs=ADA_TWD") as websocket:
                self._parse_and_log_ticker_response(await websocket.recv())
        except Exception as e:
            self.logger.program(f"Strategy:_handle_price_check(): {e}")
             

    def _parse_and_log_ticker_response(self, ticker: str) -> None:
        ticker = json.loads(ticker)
        self.logger.price(f"{ticker['datetime']},{ticker['pair']},{ticker['lastPrice']},{ticker['priceChange24hr']},{ticker['volume24hr']}")
