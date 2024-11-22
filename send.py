import requests

url = 'http://127.0.0.1:5000/receive'
data = {"message": "Hello, server!"}

response = requests.post(url, json=data)
print(response.json())
