from flask import jsonify, request
from api import app
from database import connect_to_db, get_player_info, get_transaction_history
from transfer import process_transfer_confirmation

@app.route('/api/balance', methods=['GET'])
def get_balance():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Authorization token required'}), 401

    db_connection, db_cursor = connect_to_db()
    user_info = get_player_info(db_cursor, token)

    if not user_info:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({'balance': user_info[2]})

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Authorization token required'}), 401

    db_connection, db_cursor = connect_to_db()
    user_info = get_player_info(db_cursor, token)

    if not user_info:
        return jsonify({'error': 'User not found'}), 404

    transactions = get_transaction_history(db_cursor, user_info[0], limit=10)
    return jsonify({'transactions': transactions})

@app.route('/api/transfer', methods=['POST'])
def transfer_funds():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Authorization token required'}), 401

    data = request.json
    recipient_id = data.get('recipient_id')
    amount = data.get('amount')
    comment = data.get('comment')

    if not recipient_id or not amount:
        return jsonify({'error': 'Recipient ID and amount are required'}), 400

    db_connection, db_cursor = connect_to_db()
    user_info = get_player_info(db_cursor, token)

    if not user_info:
        return jsonify({'error': 'User not found'}), 404

    sender_id = user_info[0]
    if sender_id == recipient_id:
        return jsonify({'error': 'Cannot transfer to yourself'}), 400

    process_transfer_confirmation(None, sender_id, "подтвердить", db_cursor, db_connection)
    return jsonify({'message': 'Transfer successful'})