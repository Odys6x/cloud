import requests
import time

# Local League client URLs
player_url = "https://127.0.0.1:2999/liveclientdata/playerlist"
game_stats_url = "https://127.0.0.1:2999/liveclientdata/gamestats"
event_url = "https://127.0.0.1:2999/liveclientdata/eventdata"

# Streamlit Cloud endpoint
receiver_url = "https://your-streamlit-cloud-url.com/receive"

def fetch_data(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}

def send_data():
    player_data = fetch_data(player_url)
    game_stats = fetch_data(game_stats_url)
    event_data = fetch_data(event_url)
    payload = {"player_data": player_data, "game_stats": game_stats, "event_data": event_data}
    try:
        response = requests.post(receiver_url, json=payload)
        response.raise_for_status()
        print("Data successfully sent to Streamlit receiver.")
    except Exception as e:
        print(f"Error sending data: {e}")

if __name__ == "__main__":
    while True:
        send_data()
        time.sleep(5)
