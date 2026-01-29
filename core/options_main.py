
# option_trader.py
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
from dotenv import load_dotenv
from logzero import logger
from utils.load_instrument_token import load_options_token
import threading
import requests, os, json, pyotp, math, time

class OptionTrader:
    def __init__(self, client_path):
        try:
            print(client_path)
            load_dotenv(client_path)
            self.CLIENT = os.getenv('CLIENT')
            self.API = os.getenv('API')
            self.MPIN = os.getenv('PIN')
            self.TOTP_Secret = os.getenv('TOTP')
        except Exception as e:
            print("check the file contents")
            print("error caused:", e)

        # --- UI callbacks (Textual will set these) ---
        self.on_status = None           # def on_status(text: str) -> None
        self.on_price = None            # def on_price(token: str, ltp: float) -> None
        self.on_diff = None             # def on_diff(atm: int, ce_ltp: float, pe_ltp: float, diff: float) -> None
        self.on_preview = None
        self.on_auth = None             # def on_auth(client_name: str, funds: float) -> None
        self.on_tokens_changed = None   # def on_tokens_changed(atm: int, ce_token: str, pe_token: str) -> None
        self.on_trade_signal = None     # already used by you

        self.obj = SmartConnect(api_key=self.API, disable_ssl=True)
        self.sws = None
        self.stop_event = threading.Event()
        self.subscrption = {"mode": 1, "exchangeType": 2, "tokens": []}
        self.ltp_cache = {}
        self.current_atm = None
        self.ce_token = None
        self.pe_token = None
        self.preview_ce_token = None
        self.preview_pe_token = None
        self.AUTH_TOKEN = None
        self.FEED_TOKEN = None
        self.name = None
        self.trade_taken = False
        self.option_token_map, self.token_symbol_map = load_options_token()

    # --- small helpers to safely emit events ---
    def _emit_status(self, text: str):
        if callable(self.on_status):
            try:
                self.on_status(text)
            except Exception:
                pass

    def _emit_price(self, token: str, ltp: float):
        if callable(self.on_price):
            try:
                self.on_price(token, ltp)
            except Exception:
                pass

    def _emit_diff(self, atm: int, ce_ltp: float, pe_ltp: float, diff: float):
        if callable(self.on_diff):
            try:
                self.on_diff(atm, ce_ltp, pe_ltp, diff)
            except Exception:
                pass
            
    def _emit_preview(self, atm: int, ce_ltp: float, pe_ltp: float, diff: float):
        if callable(self.on_preview):
            try:
                self.on_preview(atm, ce_ltp, pe_ltp, diff)
            except Exception:
                pass

    def _emit_auth(self, client_name: str, funds: float):
        if callable(self.on_auth):
            try:
                self.on_auth(client_name, funds)
            except Exception:
                pass

    def _emit_tokens_changed(self, atm: int, ce_token: str, pe_token: str):
        if callable(self.on_tokens_changed):
            try:
                self.on_tokens_changed(atm, ce_token, pe_token)
            except Exception:
                pass

    # --- business logic unchanged, but calls UI hooks ---
    def authenticate(self):
        totp = pyotp.TOTP(self.TOTP_Secret).now()
        session = self.obj.generateSession(self.CLIENT, self.MPIN, totp)
        data = session['data']
        self.AUTH_TOKEN = data['jwtToken']
        self.FEED_TOKEN = data['feedToken']
        self.name = data['name']
        self._emit_status(f"Login successful for {self.name}")

        with open(f"{self.CLIENT}_session.json", 'w') as f:
            json.dump(session['data'], f)
            self._emit_status("Session tokens saved")

        # funds
        try:
            funds = self.get_fund_details()
            self._emit_auth(self.name, float(funds))
        except Exception as e:
            self._emit_status(f"Failed to fetch funds: {e!r}")

    def get_fund_details(self):
        rms = self.obj.rmsLimit()        
        return rms['data']['availablecash']

    def get_atm_strike(self, price, step=50):
        return math.ceil(price / step) * step

    def get_ce_pe_tokens(self, strike):
        ce = self.option_token_map.get((strike, "CE"))
        pe = self.option_token_map.get((strike, "PE"))
        return ce, pe

    def on_open(self, ws):
        self._emit_status("WebSocket opened")
        self.sws.subscribe(
            correlation_id="NIFTY_SPOT",
            mode=1,
            token_list=[{"exchangeType": 1, "tokens": ["26000"]}]  # NSE index token
        )

    def on_data(self, ws, message):
        token = message.get('token')
        if token:
            ltp = message.get('last_traded_price') / 100
            self.ltp_cache[token] = ltp
            self._emit_price(token, ltp)

    def on_error(self, ws, error):
        self._emit_status(f"WebSocket error: {error}")

    def on_close(self, ws):
        self._emit_status("WebSocket closed")

    def create_websocket(self):
        self.sws = SmartWebSocketV2(self.AUTH_TOKEN, self.API, self.CLIENT, self.FEED_TOKEN, max_retry_attempt=0)
        self.sws.on_open = self.on_open
        self.sws.on_data = self.on_data
        self.sws.on_error = self.on_error
        self.sws.on_close = self.on_close

    def emit_trade_signal(self, trade_signal):
        if hasattr(self, "on_trade_signal") and callable(self.on_trade_signal):
            self.on_trade_signal(trade_signal)
        else:
            self._emit_status("No trade signal handler attached")

    def build_trade_signal(self):
        return {
            "startergy": "ATM_DIFF_SELL",
            "legs": [
                {"symbol": self.token_symbol_map[self.ce_token], "token": self.ce_token},
                {"symbol": self.token_symbol_map[self.pe_token], "token": self.pe_token},
            ]
        }

    def preview(self,spot :str):
        self.spot = spot
        try:
            self.preview_ce_token, self.preview_pe_token = self.get_ce_pe_tokens(self.spot)
            
            if not self.preview_ce_token or not self.preview_pe_token:
                self._emit_status("Preview tokens not found for that spot.")
                return
            self.sws.subscribe(
                correlation_id="preview",
                mode=1,
                token_list=[{"exchangeType":2,"tokens":[self.preview_ce_token,self.preview_pe_token]}]
            )
            self._emit_status("Preview added")
        except:
            self._emit_status("Something went wrong in preview")
        
        
    def main(self):
        # Runs in a background thread
        while not self.stop_event.is_set():
            if "26000" in self.ltp_cache:
                nifty_price = self.ltp_cache["26000"]
                atm = self.get_atm_strike(nifty_price)
                if atm != self.current_atm:
                    old_ce, old_pe = self.ce_token, self.pe_token
                    self.ce_token, self.pe_token = self.get_ce_pe_tokens(atm)
                    if self.ce_token and self.pe_token:
                        # Unsubscribe old
                        if old_ce and old_pe:
                            self.sws.unsubscribe(
                                correlation_id="REMOVE_OPT",
                                mode=1,
                                token_list=[{"exchangeType": 2, "tokens": [old_ce, old_pe]}]
                            )
                        # Subscribe new
                        self.sws.subscribe(
                            correlation_id="ADD_OPT",
                            mode=1,
                            token_list=[{"exchangeType": 2, "tokens": [self.ce_token, self.pe_token]}]
                        )
                        self.current_atm = atm
                        self._emit_tokens_changed(atm, self.ce_token, self.pe_token)
            try:
            # CE & PE values if available
                if self.ce_token in self.ltp_cache and self.pe_token in self.ltp_cache:
                    ce_value = self.ltp_cache[self.ce_token]
                    pe_value = self.ltp_cache[self.pe_token]
                    diff = abs(ce_value - pe_value)

                    # Let UI show a single-line summary                
                    self._emit_diff(self.current_atm, ce_value, pe_value, diff)

                    if diff <= 3 and not self.trade_taken:
                        self._emit_status("Entry condition met")
                        signal = self.build_trade_signal()
                        self.trade_taken = True
                        self.emit_trade_signal(signal)
                    
                if self.preview_ce_token in self.ltp_cache and self.preview_pe_token in self.ltp_cache:
                    preview_ce_value = self.ltp_cache[self.preview_ce_token]
                    preview_pe_value = self.ltp_cache[self.preview_pe_token]
                    
                    preview_diff = abs(preview_ce_value - preview_pe_value)
                    
                    self._emit_preview(self.spot,preview_ce_value,preview_pe_value,preview_diff)
            except Exception as e:
                self._emit_status("error: ",e)
            time.sleep(0.5)

    def start_connection(self):
        self.create_websocket()
        threading.Thread(target=self.main, daemon=True).start()
        self.sws.connect()

    def stop(self):
        self.stop_event.set()
        try:
            if self.sws:
                self.sws.close_connection()
        except Exception:
            pass

    def place_sell_order(self, symbol, token):
        try:
            orderparams = {
                "variety": "NORMAL",
                "tradingsymbol": symbol,
                "symboltoken": token,
                "transactiontype": "SELL",
                "exchange": "NFO",
                "ordertype": "MARKET",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": "0",
                "quantity": "65"
            }
            orderid = self.obj.placeOrder(orderparams)
            logger.info(f"Order placed successfully for {self.CLIENT}, Order ID: {orderid}")
            book = self.obj.orderBook()
            order_response = book['data'][0]['text']
            logger.info(f"{self.CLIENT}: {order_response}")
            self._emit_status(f"Order placed: {orderid} | {order_response}")
        except Exception as e:
            self._emit_status(f"Order placement failed: {e}")
