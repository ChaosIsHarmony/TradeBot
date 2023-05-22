import math
from ..libs import common_lib as cl
from ..libs import parser_lib as pl

# ---------------------
# COMMUNAL MOCK DATA
# ---------------------
BALANCES = [
            {
                "currency": "twd",
                "amount": "2904",
                "available": "2904",
                "stake": "0",
                "tradable": True
            },
            {
                "currency": "ada",
                "amount": "3000",
                "available": "2000",
                "stake": "0",
                "tradable": True
            },
        ]

BOOK_ORDERS = {
        "asks": [{ "price": "55911", "amount": "4.2288", "count": 1, "total": "4.2288" }],
        "bids": [{ "price": "55993", "amount": "1.57730536", "count": 1, "total": "1.57730536" }]
        }

ORDERS = [
            {
                "id": "1669239183",
                "pair": "eth_twd",
                "price": "56409",
                "avgExecutionPrice": "56409",
                "action": "BUY",
                "type": "LIMIT",
                "createdTimestamp": 1684223229706,
                "updatedTimestamp": 1684223229726,
                "status": 2,
                "originalAmount": "0.01772767",
                "remainingAmount": "0",
                "executedAmount": "0.01772767",
                "fee": "0.00003546",
                "feeSymbol": "eth",
                "bitoFee": "0",
                "total": "1000.00013703",
                "seq": "ETHTWD5903103246",
                "stopPrice": "0",
                "timeInForce": "GTC"
            },
            {
                "id": "1669239184",
                "pair": "ada_twd",
                "price": "11.04",
                "avgExecutionPrice": "11.04",
                "action": "BUY",
                "type": "LIMIT",
                "createdTimestamp": 1684223229736,
                "updatedTimestamp": 1684223229746,
                "status": 1,
                "originalAmount": "1104.00003434",
                "remainingAmount": "1104.00003434",
                "executedAmount": "0",
                "fee": "1.58238911",
                "feeSymbol": "twd",
                "bitoFee": "0",
                "total": "1000.00013703",
                "seq": "ADATWD5903103246",
                "stopPrice": "0",
                "timeInForce": "GTC"
            },
            {
                "id": "1669239185",
                "pair": "eth_twd",
                "price": "56409",
                "avgExecutionPrice": "56409",
                "action": "SELL",
                "type": "LIMIT",
                "createdTimestamp": 1684223229756,
                "updatedTimestamp": 1684223229766,
                "status": 1,
                "originalAmount": "0.01772767",
                "remainingAmount": "0.00772767",
                "executedAmount": "0.01",
                "fee": "5.85245278",
                "feeSymbol": "twd",
                "bitoFee": "0",
                "total": "1000.00013703",
                "seq": "ETHTWD5903103247",
                "stopPrice": "0",
                "timeInForce": "GTC"
            },
            {
                "id": "1669239186",
                "pair": "ada_twd",
                "price": "11.04",
                "avgExecutionPrice": "11.04",
                "action": "BUY",
                "type": "LIMIT",
                "createdTimestamp": 1684223229776,
                "updatedTimestamp": 1684223229786,
                "status": 2,
                "originalAmount": "1104.00003434",
                "remainingAmount": "0",
                "executedAmount": "1104.00003434",
                "fee": "0",
                "feeSymbol": "twd",
                "bitoFee": "0",
                "total": "1000.00013703",
                "seq": "ADATWD5903103247",
                "stopPrice": "0",
                "timeInForce": "GTC"
            }
        ]

TICKER_OBJECT = {
                    "pair": "sol_twd",
                    "lastPrice": "601.18",
                    "isBuyer": False,
                    "priceChange24hr": "-1.27",
                    "volume24hr": "1029.912",
                    "high24hr": "610.17",
                    "low24hr": "600.03"
                }


# ---------------------
# TESTS
# ---------------------
def test_parse_most_recent_order():
    print("------------------")
    print("STARTING TESTS: test_parse_most_recent_order")

    # run function
    output = pl.parse_most_recent_order(ORDERS)

    # check output
    assert output[0] == "1669239186", f"Actual Id: {output[0]}"
    assert output[1] == 2, f"Actual Status: {output[1]}"
    
    print("ALL TESTS COMPLETED SUCCESSFULLY")


def test_parse_order_total():
    print("------------------")
    print("STARTING TESTS: test_parse_order_total")

    # run function
    output = pl.parse_order_total(ORDERS[2])

    # check output
    assert math.isclose(output[0], 56409*0.01), f"Actual Total: {output[0]}"
    assert output[1] == 1, f"Actual Status: {output[1]}"
    
    print("ALL TESTS COMPLETED SUCCESSFULLY")


def test_parse_balance():
    print("------------------")
    print("STARTING TESTS: test_parse_balance")

    # run function
    output = pl.parse_balance(BALANCES, "ada")

    # check output
    assert math.isclose(output[1], float(BALANCES[1]["amount"])), f"Actual Total: {output[1]}"
    assert math.isclose(output[0], float(BALANCES[1]["available"])), f"Actual Available: {output[0]}"

    # check faulty input
    exceptionRaised = False
    try:
        pl.parse_balance([{"bobo":1}],"ada")
    except Exception:
        exceptionRaised = True
    assert exceptionRaised, "Exception was not raised on faulty input"
    
    print("ALL TESTS COMPLETED SUCCESSFULLY")


def test_parse_ticker_price():
    print("------------------")
    print("STARTING TESTS: test_parse_ticker_price")

    # run function
    output = pl.parse_ticker_price(TICKER_OBJECT)

    # check output
    assert math.isclose(output[0], float(TICKER_OBJECT["lastPrice"])), f"Last Price: {output[0]}"
    assert math.isclose(output[1], float(TICKER_OBJECT["priceChange24hr"])), f"Daily Price Delta: {output[1]}"

    print("ALL TESTS COMPLETED SUCCESSFULLY")


def test_parse_order_book_orders():
    print("------------------")
    print("STARTING TESTS: test_parse_order_book_orders")

    # run function
    output_ask_found = pl.parse_order_book_orders(BOOK_ORDERS,55911,False)
    output_ask_not_found_price = pl.parse_order_book_orders(BOOK_ORDERS,55910,False)

    output_bid_found = pl.parse_order_book_orders(BOOK_ORDERS,55993,True)
    output_bid_not_found_price = pl.parse_order_book_orders(BOOK_ORDERS,55994,True)

    # check output
    PRICE = 0
    AMOUNT = 1
    assert output_ask_found[PRICE] > 0.0, "Failed on finding satsifactory ask (price)" 
    assert output_ask_found[AMOUNT] > 0.0, "Failed on finding satsifactory ask (amount)" 
    assert output_ask_not_found_price[PRICE] < 0.0, "Failed on filtering asks for price (price)" 
    assert math.isclose(output_ask_not_found_price[AMOUNT], 0.0), "Failed on filtering asks for price (amount)" 

    assert output_bid_found[PRICE] > 0.0, "Failed on finding satsifactory bid (price)"
    assert output_bid_found[AMOUNT] > 0.0, "Failed on finding satsifactory bid (amount)"
    assert output_bid_not_found_price[PRICE] < 0.0, "Failed on filtering bids for price (price)"
    assert math.isclose(output_bid_not_found_price[AMOUNT], 0.0), "Failed on filtering bids for price (amount)"

    print("ALL TESTS COMPLETED SUCCESSFULLY")



def run_all_tests():
    print("---------------------------")
    print("------------------")
    print("STARTING PARSER LIBRARY TESTS")
    print("------------------")
    print("---------------------------")

    test_parse_most_recent_order()
    test_parse_order_total()
    test_parse_balance()
    test_parse_ticker_price()
    test_parse_order_book_orders()

    print("---------------------------")
    print("------------------")
    print("ALL PARSER LIBRARY TESTS COMPLETED")
    print("------------------")
    print("---------------------------")
