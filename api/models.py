from database import get_player_info, get_transaction_history, update_user

def get_user_balance(user_id):
    user_info = get_player_info(None, user_id)  # assuming cursor is managed inside get_player_info
    if user_info:
        return user_info[2]  # balance
    return None

def get_user_transactions(user_id):
    transactions = get_transaction_history(None, user_id, limit=50)  # assuming cursor is managed inside get_transaction_history
    return transactions

def transfer_funds(sender_id, recipient_id, amount, comment):
    db_connection, db_cursor = connect_to_db()  # assuming connect_to_db is a function that returns a connection and cursor
    sender_info = get_player_info(db_cursor, sender_id)
    recipient_info = get_player_info(db_cursor, recipient_id)

    if not sender_info or not recipient_info or sender_info[2] < amount:
        return False

    update_user(db_cursor, db_connection, sender_id, {'balance': sender_info[2] - amount})
    update_user(db_cursor, db_connection, recipient_id, {'balance': recipient_info[2] + amount})

    try:
        query = "INSERT INTO transactions (sender_id, recipient_id, amount, comment) VALUES (%s, %s, %s, %s)"
        db_cursor.execute(query, (sender_id, recipient_id, amount, comment))
        db_connection.commit()
        return True
    except Exception as e:
        db_connection.rollback()
        return False
    finally:
        db_cursor.close()
        db_connection.close()