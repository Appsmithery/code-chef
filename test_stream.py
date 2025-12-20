import json

import requests

url = "https://codechef.appsmithery.co/chat/stream"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "gt5Ae88fz-inOpFmRf1kVAkOJSV3enR7qr8ri1V2so0",
}
data = {"message": "hello", "user_id": "test_user"}

response = requests.post(url, headers=headers, json=data, stream=True, verify=False)

for line in response.iter_lines():
    if line:
        print(line.decode("utf-8"))
