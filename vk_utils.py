import vk_api
import random
import logging
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll
from config import CONFIG

def connect_to_vk():
    try:
        vk_session = vk_api.VkApi(token=CONFIG['ACCESS_TOKEN'])
        longpoll = VkLongPoll(vk_session)
        vk = vk_session.get_api()
        return vk, longpoll
    except Exception as e:
        logging.error(f"Не удалось подключиться к VK API: {e}")
        return None, None

def send_message(vk, user_id, message, keyboard=None):
    if vk is None:
        logging.error("Ошибка: VK объект не инициализирован.")
        return
    try:
        vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=random.randint(1, 2**31),
            keyboard=keyboard.get_keyboard() if keyboard else None
        )
    except Exception as e:
        logging.error(f"Не удалось отправить сообщение: {e}")

def build_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button('📲 Профиль', VkKeyboardColor.PRIMARY, payload={"command": "профиль"})
    keyboard.add_line()
    keyboard.add_button('⛏️ Майнить', VkKeyboardColor.POSITIVE, payload={"command": "майнить"})
    keyboard.add_button('💸 Перевод', VkKeyboardColor.POSITIVE, payload={"command": "перевод"})
    keyboard.add_line()
    keyboard.add_button('🔑 API', VkKeyboardColor.SECONDARY, payload={"command": "api"})
    return keyboard

def build_inline_profile_keyboard():
    keyboard = VkKeyboard(inline=True)
    keyboard.add_button('✏️ Сменить имя', VkKeyboardColor.PRIMARY, payload={'command': 'сменить имя'})
    keyboard.add_button('📜 Транзакции', VkKeyboardColor.SECONDARY, payload={'command': 'транзакции'})
    return keyboard

def build_inline_transactions_keyboard():
    keyboard = VkKeyboard(inline=True)
    keyboard.add_button('Все переводы', VkKeyboardColor.PRIMARY, payload={'command': 'все переводы'})
    return keyboard