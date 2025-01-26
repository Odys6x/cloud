from flask import Flask, jsonify, request
import requests
from openai import OpenAI

app = Flask(__name__)

# OpenAI API Key
client = OpenAI(api_key="yourapikey")
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
    # Fetch and combine data
    player_data = fetch_data(player_url)
    game_stats = fetch_data(game_stats_url)
    event_data = fetch_data(event_url)

    combined_data = {
        "player_data": player_data,
        "game_stats": game_stats,
        "event_data": event_data
    }

    # Call OpenAI API to summarize
    try:
        completion = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides summaries and reasoning for League of Legends game data in JSON format. Perhaps do explain why players did well and why some did not"},
                {"role": "user", "content": str(combined_data)}
            ]
        )
        summary = completion.choices[0].message.content
        return jsonify({"summary": summary})
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return jsonify({"error": "Failed to summarize data"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
