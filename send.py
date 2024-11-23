from flask import Flask, jsonify
import requests

# Flask setup
app = Flask(__name__)

# Local League client URLs
player_url = "https://127.0.0.1:2999/liveclientdata/playerlist"
game_stats_url = "https://127.0.0.1:2999/liveclientdata/gamestats"
event_url = "https://127.0.0.1:2999/liveclientdata/eventdata"


def fetch_data(url):
    """Fetch data from the specified League client API."""
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        print(f"Successfully fetched data from {url}: {response.json()}")  # Debug: Print fetched data
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}

@app.route('/data', methods=['GET'])
def get_data():
    """Expose League client data as a JSON response."""
    print("Fetching player data...")
    player_data = fetch_data(player_url)

    print("Fetching game stats...")
    game_stats = fetch_data(game_stats_url)

    print("Fetching event data...")
    event_data = fetch_data(event_url)

    # Debug: Print all data before returning
    print("Fetched data:")
    print({
        "player_data": player_data,
        "game_stats": game_stats,
        "event_data": event_data
    })

    return jsonify({
        "player_data": player_data,
        "game_stats": game_stats,
        "event_data": event_data
    })

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, debug=False)
