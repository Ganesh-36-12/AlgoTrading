from datetime import datetime, timedelta
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
    days_to_tuesday = (1-today.weekday()) % 7
    
    current_week_expiry = pd.to_datetime(today+timedelta(days=days_to_tuesday))
    week_start = pd.to_datetime(current_week_expiry - timedelta(days=6))
    
    opt_df =opt_df[(opt_df['expiry']>=week_start) & (opt_df['expiry']<=current_week_expiry)]
    option_token_map = {}
    token_symbol_map = {}
    for _, row in opt_df.iterrows():
        option_token_map[(int(float(row["strike"])), row["symbol"][-2:])] = str(row["token"])
        token_symbol_map[str(row["token"])] = row["symbol"]
    return option_token_map,token_symbol_map
