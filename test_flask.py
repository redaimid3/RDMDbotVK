from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/balance', methods=['GET'])
def get_balance():
    response = {
        'balance': 1000
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
