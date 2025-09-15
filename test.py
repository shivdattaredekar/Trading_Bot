import requests
import json
from src.tradingsetup.config.settings import APP_URL, GRANT_TYPE2, PIN, REFRESH_TOKEN, CLIENT_ID, SECRET_KEY
import hashlib  

url = APP_URL
input_string = f"{CLIENT_ID}:{SECRET_KEY}"
appidhash = hashlib.sha256(input_string.encode()).hexdigest()

appidhash = '056caa979a8c4356a58fb6c5cb230efcfbfe938711163502b8dbfb2f57b6c93c'

print("APP_URL:", APP_URL, type(APP_URL))
print("GRANT_TYPE2:", GRANT_TYPE2, type(GRANT_TYPE2))
print("PIN:", PIN, type(PIN))
print("REFRESH_TOKEN:", REFRESH_TOKEN, type(REFRESH_TOKEN))
print("CLIENT_ID:", CLIENT_ID, type(CLIENT_ID))
print("SECRET_KEY:", SECRET_KEY, type(SECRET_KEY))
print("appidhash", appidhash, type(appidhash))



headers = {
    "Content-Type": "application/json"
}

payload = {
    "grant_type": GRANT_TYPE2,
    "appIdHash": appidhash,
    "refresh_token": REFRESH_TOKEN,
    "pin": PIN
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(payload))
except Exception as e:
    print(e)

# Print the response
print("Status Code:", response.status_code)
print("Response JSON:", response.json())