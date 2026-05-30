from flask import Flask, request
import requests

app=Flask(__name__)

@app.route("/placeOrder",methods=['POST'])
def auth():
    data = request.get_json()
    headers = {
        'Authorization': data.get('AUTH_TOKEN'),
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-UserType': 'USER',
        'X-SourceID': 'WEB',
        'X-PrivateKey': data.get('API')
    }
    payload = {
        "variety": "NORMAL",
        "tradingsymbol": data.get('symbol'),
        "symboltoken": data.get('token'),
        "transactiontype": data.get('B_S'),
        "exchange": "NFO",
        "ordertype": "MARKET",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "price": "0",
        "quantity": 65
    }
    
    r = requests.post(url="https://apiconnect.angelone.in/rest/secure/angelbroking/order/v1/placeOrder",
                    headers=headers,
                    params=payload,
                    verify=False)
    print(r.status_code)

    return r.content

@app.route('/test',methods=['GET'])
def test():
    print("Flask app running successful")
    return "Hellloo World"


app.run(host='0.0.0.0',port=6000,debug=True)
    

