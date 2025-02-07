from flask import Flask, jsonify, request
import requests
from openai import OpenAI

app = Flask(__name__)

# OpenAI API Key
client = OpenAI(api_key="")

# URLs for data fetching
player_url = "https://127.0.0.1:2999/liveclientdata/playerlist"
game_stats_url = "https://127.0.0.1:2999/liveclientdata/gamestats"
event_url = "https://127.0.0.1:2999/liveclientdata/eventdata"

def fetch_data(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}


@app.route('/data', methods=['GET'])
def get_data():
    player_data = fetch_data(player_url)
    game_stats = fetch_data(game_stats_url)
    event_data = fetch_data(event_url)

    return jsonify({
        "player_data": player_data,
        "game_stats": game_stats,
        "event_data": event_data
    })


@app.route('/summarize', methods=['GET'])
def summarize_data():
    try:
        player_data = fetch_data(player_url)
        game_stats = fetch_data(game_stats_url)
        event_data = fetch_data(event_url)

        # Split data into smaller chunks
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Provide a brief, focused summary of this League of Legends game data. Focus on key events and player performance metrics."},
                {"role": "user", "content": str({
                    "player_data": player_data[:5],  # Limit player data
                    "game_stats": game_stats,
                    "key_events": event_data[-10:]  # Last 10 events only
                })}
            ]
        )
        return jsonify({"summary": completion.choices[0].message.content})
    except Exception as e:
        print(f"Error details: {str(e)}")
        return jsonify({"error": "Failed to summarize data"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
