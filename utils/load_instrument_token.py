from datetime import datetime, timedelta
from bidict import bidict
from glob import glob
import os
import pandas as pd
import requests,json


def load_options_token():
    files = glob("tickers*") 
    formatted_today = datetime.today().date().strftime("%d%m%Y")
    
    try:
        with open(f"tickers_{formatted_today}.json", "r") as file:
            instrument_list= json.load(file)
            
    except FileNotFoundError:
        try:
            os.remove(files[0])
            print(f"'{files}' has been removed successfully.")
        except Exception as e:
            print(f"Error: '{e}'")
            
        with open(f"tickers_{formatted_today}.json", 'w') as json_file:
            instrument_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
            response = requests.get(instrument_url,verify=False)
            instrument_list = response.json()
            json.dump(instrument_list, json_file, indent=4)
            
    df = pd.DataFrame(instrument_list)
    df = df[ (df['name'] == "NIFTY") & (df['instrumenttype'] == "OPTIDX")].copy()
    
    df["expiry"] = pd.to_datetime(df['expiry'],format="%d%b%Y")
    df['strike'] = df['strike'].astype(float) / 100
    
    today = pd.Timestamp.today().normalize()
    max_date = today + pd.Timedelta(days=30)
    df = df[(df['expiry'] >= today) & (df['expiry'] <= max_date)]
    
    # current_expiry = df['expiry'].min()
    
    sorted_dates = sorted(df['expiry'].unique())
    expiry_list = [d.strftime('%d%b%y').upper() for d in sorted_dates]
    
    symbol_token_map = bidict(zip(df['symbol'], df['token']))
    
    return expiry_list, symbol_token_map 

def get_current_expiry():
    today = datetime.today().date()
    days_to_tuesday = (1-today.weekday()) % 7
    current_week_expiry = pd.to_datetime(today+timedelta(days=days_to_tuesday)).strftime('%d%b%y').upper()
    
    return current_week_expiry
