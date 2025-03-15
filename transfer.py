import logging
from datetime import datetime
from vk_utils import send_message, build_inline_transactions_keyboard
from database import get_player_info, update_user, get_transaction_history
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import re
import mysql.connector

transfer_sessions = {}

def parse_recipient(text, message, sender_id, vk):
    username = extract_username_from_url(text)
    if username:
        user_id, screen_name = lookup_vk_user(username, vk)
        if user_id and user_id != str(sender_id):
            return user_id, screen_name

    user_id = extract_user_id_from_mention(text)
    if user_id and str(user_id) != str(sender_id):
        return user_id, f"vk.com/id{user_id}"

    if isinstance(message, dict):
        fwd_msgs = message.get("fwd_messages", [])
        if fwd_msgs:
            recipient_id = fwd_msgs[0].get("from_id")
            if recipient_id and str(recipient_id) != str(sender_id):
                return str(recipient_id), f"vk.com/id{recipient_id}"
        
        reply = message.get("reply_message")
        if reply:
            recipient_id = reply.get("from_id")
            if recipient_id and str(reply.get("from_id")) != str(sender_id):
                return str(reply.get("from_id")), f"vk.com/id{reply.get('from_id')}"
    
    return None, None

def extract_username_from_url(url):
    match = re.search(r"vk\.com/([A-Za-z_]+\w*)", url)
    return match.group(1) if match else None

def extract_user_id_from_mention(mention):
    match = re.search(r"\[id(\d+)\|@", mention)
    return match.group(1) if match else None

def lookup_vk_user(username, vk):
    try:
        response = vk.users.get(user_ids=username, fields="screen_name")
        if response and isinstance(response, list) and response[0].get("id"):
            user_id = str(response[0]["id"])
            screen_name = response[0].get("screen_name", username)
            return user_id, screen_name
    except Exception as e:
        logging.error(f"Ошибка при поиске пользователя по юзернейму {username}: {e}")
    return None, None

def initiate_transfer(user_id, message, vk):
    if isinstance(message, str):
        message = {"text": message}

    transfer_sessions[str(user_id)] = {"stage": "recipient", "sender_id": str(user_id)}
    logging.debug(f"Инициализирована сессия перевода для пользователя {user_id}: {transfer_sessions[str(user_id)]}")
    reply = message.get("reply_message")
    text = message.get("text", "")
    
    sum_in_text = None
    for part in text.split():
        try:
            sum_in_text = int(part)
            break
        except:
            continue

    peer_id = message.get("peer_id") or user_id
    if reply and reply.get("from_id"):
        if str(reply.get("from_id")) == str(user_id):
            send_message(vk, peer_id, "Нельзя переводить самому себе.")
            del transfer_sessions[str(user_id)]
            return
        transfer_sessions[str(user_id)]["recipient"] = str(reply.get("from_id"))
        transfer_sessions[str(user_id)]["recipient_name"] = f"vk.com/id{reply.get('from_id')}"
        if sum_in_text is not None:
            transfer_sessions[str(user_id)]["amount"] = sum_in_text
            transfer_sessions[str(user_id)]["stage"] = "confirm"
            send_transfer_confirmation(user_id, vk, peer_id)
        else:
            transfer_sessions[str(user_id)]["stage"] = "amount"
            send_message(vk, peer_id, "Введите сумму для перевода:")
    else:
        recipient, recipient_name = parse_recipient(text, message, user_id, vk)
        if recipient:
            transfer_sessions[str(user_id)]["recipient"] = recipient
            transfer_sessions[str(user_id)]["recipient_name"] = recipient_name
            if sum_in_text is not None:
                transfer_sessions[str(user_id)]["amount"] = sum_in_text
                transfer_sessions[str(user_id)]["stage"] = "confirm"
                send_transfer_confirmation(user_id, vk, peer_id)
            else:
                transfer_sessions[str(user_id)]["stage"] = "amount"
                send_message(vk, peer_id, "Введите сумму для перевода:")
        else:
            send_message(vk, peer_id, "Введите ссылку, тег или упоминание игрока, которому нужно перевести средства. Либо ответьте на сообщение от него.")

def send_transfer_confirmation(user_id, vk, peer_id):
    session = transfer_sessions.get(str(user_id))
    if not session:
        logging.debug(f"Сессия перевода не найдена для пользователя {user_id}")
        return
    amount = session.get("amount")
    recipient = session.get("recipient")
    recipient_name = session.get("recipient_name")
    confirmation_msg = (
        f"💸 Подтвердите перевод:\n"
        f"Вы хотите отправить {amount} RD игроку {recipient_name}.\n\n"
        "Пожалуйста, подтвердите или отмените перевод, нажав соответствующую кнопку."
    )
    keyboard = VkKeyboard(inline=True)
    keyboard.add_button('✅ Подтвердить', color=VkKeyboardColor.POSITIVE, payload={'command': 'подтвердить'})
    keyboard.add_button('❌ Отменить', color=VkKeyboardColor.NEGATIVE, payload={'command': 'отменить'})
    keyboard.add_line()
    keyboard.add_button('💬 Добавить комментарий', color=VkKeyboardColor.SECONDARY, payload={'command': 'добавить_комментарий'})
    send_message(vk, user_id, confirmation_msg, keyboard)

def process_transfer(bot_event, user_id, text, vk, db_cursor, db_connection):
    session = transfer_sessions.get(str(user_id))
    if not session:
        logging.debug(f"Нет активной сессии перевода для пользователя {user_id}")
        return False
    stage = session.get("stage")
    peer_id = bot_event.message["peer_id"] if isinstance(bot_event.message, dict) else user_id

    if stage == "recipient":
        recipient, recipient_name = parse_recipient(text, bot_event.message, user_id, vk)
        if not recipient:
            send_message(vk, peer_id, "Не удалось определить получателя. Укажите ссылку, тег или упоминание игрока, либо ответьте на сообщение от него.")
            return True
        session["recipient"] = recipient
        session["recipient_name"] = recipient_name
        session["stage"] = "amount"
        send_message(vk, peer_id, "Введите сумму RD для перевода:")
        return True
    elif stage == "amount":
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError()
        except ValueError:
            send_message(vk, peer_id, "Введите корректное число для суммы перевода.")
            return True
        sender_user = get_player_info(db_cursor, user_id)
        if sender_user[2] < amount:
            send_message(vk, peer_id, f"Недостаточно средств для перевода. Текущий баланс: {sender_user[2]}.")
            del transfer_sessions[str(user_id)]
            return True
        session["amount"] = amount
        session["stage"] = "confirm"
        send_transfer_confirmation(user_id, vk, peer_id)
        return True
    elif stage == "comment":
        if len(text) > 30:
            send_message(vk, peer_id, "Комментарий слишком длинный. Пожалуйста, введите комментарий длиной до 30 символов.")
            return True
        session["comment"] = text
        session["stage"] = "confirm"
        send_transfer_confirmation(user_id, vk, peer_id)
        return True
    return False

def process_transfer_confirmation(vk, user_id, action, db_cursor, db_connection):
    session = transfer_sessions.get(str(user_id))
    if not session or session.get("stage") != "confirm":
        send_message(vk, user_id, "Сессия перевода не найдена или уже завершена.")
        return

    logging.debug(f"Processing transfer confirmation. User ID: {user_id}, Action: {action}, Session: {session}")

    sender_user = get_player_info(db_cursor, user_id)
    recipient = session.get("recipient")
    recipient_name = session.get("recipient_name")
    comment = session.get("comment", "")
    amount = session.get("amount")

    logging.debug(f"Sender: {sender_user}, Recipient: {recipient}, Amount: {amount}, Comment: {comment}")

    if action == "отменить":
        send_message(vk, user_id, "Перевод отменён.")
        del transfer_sessions[str(user_id)]
        return

    if action == "подтвердить":
        recipient_user = get_player_info(db_cursor, recipient)
        if not sender_user or not recipient_user:
            send_message(vk, user_id, "Ошибка перевода: не удалось получить данные пользователей.")
            logging.error(f"Transfer error: could not retrieve users. Sender: {sender_user}, Recipient: {recipient_user}")
            del transfer_sessions[str(user_id)]
            return

        if sender_user[2] < amount:
            send_message(vk, user_id, f"Недостаточно средств для перевода. Текущий баланс: {sender_user[2]}.")
            logging.error(f"Insufficient funds. Sender balance: {sender_user[2]}, Amount: {amount}")
            del transfer_sessions[str(user_id)]
            return

        update_user(db_cursor, db_connection, user_id, {"balance": sender_user[2] - amount})
        update_user(db_cursor, db_connection, recipient, {"balance": recipient_user[2] + amount})

        try:
            query = "INSERT INTO transactions (sender_id, recipient_id, amount, comment) VALUES (%s, %s, %s, %s)"
            db_cursor.execute(query, (user_id, recipient, amount, comment))
            db_connection.commit()
            logging.debug(f"Transaction logged successfully. Sender: {user_id}, Recipient: {recipient}, Amount: {amount}, Comment: {comment}")
        except mysql.connector.Error as err:
            logging.error(f"Ошибка при сохранении транзакции: {err}")
            send_message(vk, user_id, "Ошибка при сохранении транзакции.")
            return

        sender_user = get_player_info(db_cursor, user_id)
        recipient_user = get_player_info(db_cursor, recipient)

        send_message(
            vk, 
            user_id, 
            f"Перевод выполнен успешно! С вашего счета списано {amount} RD. Новый баланс: {sender_user[2]} RD." + (f" Комментарий: {comment}" if comment else "")
        )
        send_message(
            vk, 
            int(recipient), 
            f"Вам переведен {amount} RD от [vk.com/id{user_id}|{sender_user[1]}]." + (f" Комментарий: {comment}" if comment else "")
        )
        del transfer_sessions[str(user_id)]
        return

def format_transaction_history(transactions, db_cursor, vk_id, is_detailed=False):
    history_message = "🤝️ История переводов\n\n"
    for i, t in enumerate(transactions):
        sender_info = get_player_info(db_cursor, t[1])
        recipient_info = get_player_info(db_cursor, t[2])
        date_str = t[4].strftime("%d.%m %H:%M")
        comment = t[5] if len(t) > 5 and t[5] else ''
        if t[1] == vk_id:
            history_message += f"{i + 1}. Отправлено: [vk.com/id{t[2]}|{recipient_info[1]}] (User)\n{date_str} | {t[3]} RD" + (f"\nКомментарий: {comment}" if comment else "") + "\n\n"
        else:
            history_message += f"{i + 1}. Получено: [vk.com/id{t[1]}|{sender_info[1]}] (User)\n{date_str} | {t[3]} RD" + (f"\nКомментарий: {comment}" if comment else "") + "\n\n"
    if not is_detailed and len(transactions) == 10:
        history_message += "Нажмите 'Все переводы' для просмотра всех переводов."
    return history_message