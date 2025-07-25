from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Configuration
TARGET_HOST = 'db'  # Replace with your actual hostname
TARGET_PORT = 10001

@app.route('/', methods=['GET'])
def proxy_request():
    try:
        # Construct the target URL
        target_url = f'http://{TARGET_HOST}:{TARGET_PORT}/'

        # Forward the GET request to the target API
        response = requests.get(target_url)

        # Return the response from the target API
        return (response.text, response.status_code, response.headers.items())

    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Make sure you're running as root/admin to bind to port 80
    app.run(host='0.0.0.0', port=80)