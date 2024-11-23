import requests
import time

# Local League client URLs
player_url = "https://127.0.0.1:2999/liveclientdata/playerlist"
game_stats_url = "https://127.0.0.1:2999/liveclientdata/gamestats"
event_url = "https://127.0.0.1:2999/liveclientdata/eventdata"

# Streamlit receiver URL
receiver_url = "http://localhost:5001/receive"  # Replace with deployed Streamlit app URL if hosted remotely

def fetch_data(url):
    """Fetch data from the specified League client API."""
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}

def send_data_to_receiver(payload):
    """Send game data to the Streamlit receiver."""
    try:
        response = requests.post(receiver_url, json=payload)
        response.raise_for_status()
        print("Data successfully sent to Streamlit receiver.")
    except Exception as e:
        print(f"Error sending data to receiver: {e}")

def process_and_send_data():
    """Fetch, process, and send data to the Streamlit app."""
    # Fetch data from League client
    player_data = fetch_data(player_url)
    game_stats = fetch_data(game_stats_url)
    event_data = fetch_data(event_url)

    # Prepare the payload
    payload = {
        "player_data": player_data,
        "game_stats": game_stats,
        "event_data": event_data
    }

    # Send the payload to the Streamlit app
    send_data_to_receiver(payload)

if __name__ == "__main__":
    print("Starting local data processor...")
    while True:
        process_and_send_data()
        time.sleep(10)  # Wait 5 seconds before fetching data again
