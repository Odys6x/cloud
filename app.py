from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Global variable to store received data
received_data = []

# Route to receive and store data
@app.route('/receive', methods=['POST'])
def receive_data():
    global received_data
    # Get JSON data from the request
    data = request.json
    # Add received data to the list
    received_data.append(data)
    # Log the received data (optional)
    print(f"Received data: {data}")
    # Respond with a success message
    return jsonify({"status": "success", "received_data": data})

# Route to fetch the received data dynamically
@app.route('/data', methods=['GET'])
def get_data():
    global received_data
    # Return the received data as JSON
    return jsonify(received_data)

# Route to display the frontend
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
