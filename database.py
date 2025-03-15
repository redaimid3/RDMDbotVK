import mysql.connector
import logging
from config import CONFIG

def connect_to_db():
    try:
        db_connection = mysql.connector.connect(
            host=CONFIG['DB_HOST'],
            user=CONFIG['DB_USER'],
            password=CONFIG['DB_PASSWORD'],
            database=CONFIG['DB_NAME']
        )
        db_cursor = db_connection.cursor()
        return db_connection, db_cursor
    except mysql.connector.Error as err:
        logging.error(f"Ошибка: {err}")
        return None, None

def get_player_info(db_cursor, vk_id):
    try:
        db_cursor.execute("SELECT vk_id, nickname, balance, total_balance, clicks, start_date, user_token FROM players WHERE vk_id = %s", (vk_id,))
        player_info = db_cursor.fetchone()
        return player_info
    except mysql.connector.Error as err:
        logging.error(f"Ошибка: {err}")
        return None

def get_player_info_by_token(db_cursor, token):
    try:
        db_cursor.execute("SELECT vk_id, nickname, balance, total_balance, clicks, start_date, user_token FROM players WHERE user_token = %s", (token,))
        player_info = db_cursor.fetchone()
        return player_info
    except mysql.connector.Error as err:
        logging.error(f"Ошибка: {err}")
        return None

def get_top_players(db_cursor, limit=10):
    try:
        db_cursor.execute("SELECT vk_id, nickname, balance FROM players ORDER BY balance DESC LIMIT %s", (limit,))
        top_players = db_cursor.fetchall()
        return top_players
    except mysql.connector.Error as err:
        logging.error(f"Ошибка: {err}")
        return []

def update_user(db_cursor, db_connection, vk_id, updates):
    try:
        set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
        values = list(updates.values()) + [vk_id]
        query = f"UPDATE players SET {set_clause} WHERE vk_id = %s"
        db_cursor.execute(query, values)
        db_connection.commit()
    except mysql.connector.Error as err:
        logging.error(f"Ошибка: {err}")

def get_transaction_history(db_cursor, vk_id, limit=10):
    try:
        query = "SELECT id, sender_id, recipient_id, amount, created_at FROM transactions WHERE sender_id = %s OR recipient_id = %s ORDER BY created_at DESC LIMIT %s"
        db_cursor.execute(query, (vk_id, vk_id, limit))
        transactions = db_cursor.fetchall()
        return transactions
    except mysql.connector.Error as err:
        logging.error(f"Ошибка при получении истории транзакций: {err}")
        return []