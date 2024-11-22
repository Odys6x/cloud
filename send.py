import requests

url = 'https://winpredict-lol-f1461b39594b.herokuapp.com/receive'
data = {"message": "Hello, Flask!"}

response = requests.post(url, json=data)

# Print the raw response for debugging
print(f"Status Code: {response.status_code}")
print(f"Response Text: {response.text}")
