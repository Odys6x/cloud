from flask import Flask, jsonify
import requests

app = Flask(__name__)

player_url = "https://127.0.0.1:2999/liveclientdata/playerlist"
game_stats_url = "https://127.0.0.1:2999/liveclientdata/gamestats"
event_url = "https://127.0.0.1:2999/liveclientdata/eventdata"


def fetch_data(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        print(f"Successfully fetched data from {url}: {response.json()}")
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}

@app.route('/data', methods=['GET'])
def get_data():
    print("Fetching player data...")
    player_data = fetch_data(player_url)

    print("Fetching game stats...")
    game_stats = fetch_data(game_stats_url)

    print("Fetching event data...")
    event_data = fetch_data(event_url)

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
