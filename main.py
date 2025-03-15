import logging
import json
from vk_api.longpoll import VkLongPoll, VkEventType
from database import connect_to_db, get_player_info, get_transaction_history, update_user, get_top_players
from vk_utils import connect_to_vk, send_message, build_keyboard, build_inline_profile_keyboard, build_inline_transactions_keyboard
from transfer import initiate_transfer, process_transfer, process_transfer_confirmation, format_transaction_history
from config import CONFIG

name_change_sessions = {}
transfer_sessions = {}

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

def initiate_name_change(user_id, vk):
    name_change_sessions[str(user_id)] = True
    send_message(vk, user_id, "Введите новое имя:")

def process_name_change(user_id, text, vk, db_cursor, db_connection):
    if str(user_id) in name_change_sessions:
        if len(text) > 15:
            send_message(vk, user_id, "Имя слишком длинное. Пожалуйста, введите имя длиной до 15 символов.")
            return True
        try:
            update_user(db_cursor, db_connection, user_id, {"nickname": text})
            send_message(vk, user_id, f"Ваше имя успешно изменено на {text}.")
        except Exception as e:
            logging.error(f"Ошибка при смене имени: {e}")
            send_message(vk, user_id, "Произошла ошибка при смене имени. Попробуйте еще раз.")
        del name_change_sessions[str(user_id)]
        return True
    return False

def main():
    vk, longpoll = connect_to_vk()
    if not vk or not longpoll:
        logging.error("Не удалось подключиться к VK API")
        return

    db_connection, db_cursor = connect_to_db()
    if not db_connection or not db_cursor:
        logging.error("Не удалось подключиться к базе данных")
        return

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            user_id = event.user_id
            message = event.message
            text = event.text.lower()

            logging.debug(f"Получено сообщение от {user_id}: {text}")

            payload = None
            if hasattr(event, 'payload'):
                try:
                    payload = json.loads(event.payload)
                except json.JSONDecodeError:
                    pass

            command = payload.get("command") if payload else text

            if command in ["подтвердить", "отменить"]:
                logging.debug(f"Обработка подтверждения перевода для пользователя {user_id}")
                process_transfer_confirmation(vk, user_id, command, db_cursor, db_connection)
            elif command == "добавить_комментарий":
                if str(user_id) in transfer_sessions:
                    logging.debug(f"Активная сессия найдена для пользователя {user_id}: {transfer_sessions[str(user_id)]}")
                    transfer_sessions[str(user_id)]["stage"] = "comment"
                    send_message(vk, user_id, "Введите комментарий для перевода (до 30 символов):")
                else:
                    logging.debug(f"Нет активной сессии для пользователя {user_id}")
                    send_message(vk, user_id, "Нет активной сессии перевода. Пожалуйста, начните перевод сначала.")
            elif command == "начать":
                send_message(vk, user_id, "Добро пожаловать! Выберите действие:", build_keyboard())
            elif command == "профиль":
                player_info = get_player_info(db_cursor, user_id)
                if player_info:
                    join_date = player_info[5].strftime("%d.%m.%Y")
                    profile_info = (
                        f"📲 Профиль {player_info[1]}\n"
                        f"Айди: {player_info[0]}\n\n"
                        f"О вас:\n"
                        f"»🏦 Баланс: {player_info[2]} RD\n\n"
                        f"»♾️Баланс за всё время: {player_info[3]} RD\n\n"
                        f"»🖱️Клики: {player_info[4]}\n\n"
                        f"Присоединился: {join_date}\n"
                    )
                    send_message(vk, user_id, profile_info, build_inline_profile_keyboard())
                else:
                    send_message(vk, user_id, "Игрок не найден. Пожалуйста, зарегистрируйтесь.")
            elif command == "баланс":
                player_info = get_player_info(db_cursor, user_id)
                if player_info:
                    balance = player_info[2]
                    send_message(vk, user_id, f"Ваш баланс: {balance} RD")
                else:
                    send_message(vk, user_id, "Игрок не найден. Пожалуйста, зарегистрируйтесь.")
            elif command == "api":
                player_info = get_player_info(db_cursor, user_id)
                if player_info:
                    send_message(vk, user_id, f"Ваш API токен: {player_info[6]}")
                else:
                    send_message(vk, user_id, "Игрок не найден. Пожалуйста, зарегистрируйтесь.")
            elif command == "перевод":
                logging.debug(f"Инициализация перевода для пользователя {user_id}")
                initiate_transfer(user_id, message, vk)
                logging.debug(f"Сессия после инициализации перевода для пользователя {user_id}: {transfer_sessions.get(str(user_id))}")
            elif command == "сменить имя":
                initiate_name_change(user_id, vk)
            elif command == "транзакции":
                transactions = get_transaction_history(db_cursor, user_id, limit=10)
                history_message = format_transaction_history(transactions, db_cursor, user_id)
                send_message(vk, user_id, history_message, build_inline_transactions_keyboard())
            elif command == "все переводы":
                transactions = get_transaction_history(db_cursor, user_id, limit=50)
                history_message = format_transaction_history(transactions, db_cursor, user_id, is_detailed=True)
                send_message(vk, user_id, history_message)
            elif command == "топ":
                top_players = get_top_players(db_cursor)
                top_message = "Топ игроков по балансу:\n"
                for player in top_players:
                    top_message += (
                        f"[vk.com/id{player[0]}|{player[1]}]: {player[2]} RD\n"
                    )
                send_message(vk, user_id, top_message)
            else:
                if not process_transfer(event, user_id, text, vk, db_cursor, db_connection):
                    if not process_name_change(user_id, text, vk, db_cursor, db_connection):
                        send_message(vk, user_id, "Неизвестная команда. Пожалуйста, выберите действие:", build_keyboard())

if __name__ == "__main__":
    main()