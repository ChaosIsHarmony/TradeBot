class Order:

    def __init__(self, pair: str, action: str, orderType: str, availableBalance: float, hiPrice: float, loPrice: float = -1.0):
        self.pair = pair
        self.action = action
        self.orderType = orderType
        self.availableBalance = availableBalance
        self.hiPrice = hiPrice
        self.loPrice = loPrice


    def get_pair(self) -> str:
        return self.pair

    def get_action(self) -> str:
        return self.action

    def get_order_type(self) -> str:
        return self.orderType

    def get_available_balance(self) -> float:
        return self.availableBalance

    def get_hi_price(self) -> float:
        return self.hiPrice
    
    def get_lo_price(self) -> float:
        return self.loPrice
