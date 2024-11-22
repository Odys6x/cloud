import requests
import time

# Local game client URLs
player_url = "https://127.0.0.1:2999/liveclientdata/playerlist"
game_stats_url = "https://127.0.0.1:2999/liveclientdata/gamestats"
event_url = "https://127.0.0.1:2999/liveclientdata/eventdata"

# Cloud app URL
cloud_url = 'https://winpredict-lol-f1461b39594b.herokuapp.com/receive'  # Replace with your cloud app URL

def fetch_data(url):
    """Fetch data from the specified URL."""
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}

def process_and_send_data():
    """Fetch data, process it, and send it to the cloud."""
    # Fetch data from the local game client APIs
    player_data = fetch_data(player_url)
    game_stats = fetch_data(game_stats_url)
    event_data = fetch_data(event_url)

    # Prepare the payload for the cloud app
    payload = {
        "player_data": player_data,
        "game_stats": game_stats,
        "event_data": event_data
    }

    # Send the data to the cloud app
    try:
        response = requests.post(cloud_url, json=payload)
        response.raise_for_status()
        print("Data successfully sent to the cloud:")
        print(response.json())
    except Exception as e:
        print(f"Error sending data to the cloud: {e}")

if __name__ == "__main__":
    print("Starting local processor...")
    while True:
        process_and_send_data()
        time.sleep(5)  # Wait for 5 seconds before the next iteration
