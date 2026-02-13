from datetime import datetime, timedelta
from bidict import bidict
import pandas as pd
import requests,json

def load_options_token():
    try:
        with open("tickers.json", "r") as file:
            instrument_list= json.load(file)
            
    except FileNotFoundError:
        with open("tickers.json", 'w') as json_file:
            instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = requests.get(instrument_url,verify=False)
            instrument_list = response.json()
            json.dump(instrument_list, json_file, indent=4)


    opt_df = pd.DataFrame([i for i in instrument_list if i['name'] == "NIFTY" and i['instrumenttype'] in ['OPTIDX']])
    opt_df['expiry'] = pd.to_datetime(opt_df['expiry'],format='%d%b%Y')
    opt_df['strike'] =opt_df['strike'].astype(float).div(100).astype(int)
    opt_df =opt_df.drop(columns=["instrumenttype","exch_seg","name","lotsize","tick_size"])

    today = datetime.today().date()
    month = today + timedelta(days=30)
    days_to_tuesday = (1-today.weekday()) % 7
    
    # current_week_expiry = pd.to_datetime(today+timedelta(days=days_to_tuesday)).strftime('%d%b%Y').upper()
    
    # week_start = pd.to_datetime(current_week_expiry - timedelta(days=6))
    
    opt_df = opt_df[ (opt_df['expiry'] > pd.to_datetime(today)) & (opt_df['expiry'] <= pd.to_datetime(month)) ]
    
    expiry_list = list(map(lambda x: x.upper() ,opt_df['expiry'].unique().strftime('%d%b%y')))
    
    symbol_token_map = bidict(zip(opt_df['symbol'], opt_df['token']))
    
    return expiry_list, symbol_token_map 

def get_current_expiry():
    today = datetime.today().date()
    days_to_tuesday = (1-today.weekday()) % 7
    current_week_expiry = pd.to_datetime(today+timedelta(days=days_to_tuesday)).strftime('%d%b%y').upper()
    
    return current_week_expiry
