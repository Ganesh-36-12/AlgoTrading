from dotenv import load_dotenv
from SmartApi import SmartConnect
from logzero import logger

import os
import pyotp


class ChildTrader:
    def __init__(self,CLIENT):
        load_dotenv(f"accounts/{CLIENT}_secrets.env")
        self.CLIENT = os.getenv('CLIENT')
        self.API = os.getenv('API')
        self.MPIN = os.getenv('PIN')
        self.TOTP_Secret = os.getenv('TOTP')
        self.obj = SmartConnect(api_key=self.API,disable_ssl=True)
        self.name = None

        
    def authenticate(self):
        totp = pyotp.TOTP(self.TOTP_Secret).now()
        session = self.obj.generateSession(self.CLIENT,self.MPIN,totp)
        self.name = session['data']['name']
        print(f"{self.name} logged in as sub account")
    
    def get_fund_details(self):
        rms = self.obj.rmsLimit()
        return rms['data']['availablecash']
    
    def place_sell_order(self,symbol,token):    
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
            logger.info(f"Order placed successfully for {self.name}, Order ID: {orderid}")
            book = self.obj.orderBook()
            order_response = book['data'][0]['text']
            logger.info(f"{self.name}: {order_response}")

        except Exception as e:
            print(f"Order placement failed: {e}")