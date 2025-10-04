from dataclasses import dataclass
@dataclass
class KiteAuth:
    api_key: str
    api_secret: str
    access_token: str
class KiteBroker:
    def init(self, auth: KiteAuth):
        self.auth = auth

    def is_ready(self) -> bool:
        return all([self.auth.api_key, self.auth.api_secret, self.auth.access_token])

    def place_order(self, symbol: str, side: str, qty: int, order_type: str = "MARKET"):
        print(f"[DRY RUN] {side} {qty} {symbol} via {order_type}")
        return {"status": "ok", "symbol": symbol, "side": side, "qty": qty}
