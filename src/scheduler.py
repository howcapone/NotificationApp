import time
import threading
import telebot
from database import get_pending_notifications, move_notification_to_archive
from config import TOKEN

bot = telebot.TeleBot(TOKEN)

def check_notifications():
    while True:
        notifications = get_pending_notifications()
        for notify_id, text, user_id in notifications:
            try:
                bot.send_message(
                    user_id,
                    f"🔔 Напоминание!\n{text}\n\nСобытие должно начаться сейчас!"
                )
                # Перемещаем в архив вместо отметки как отвеченное
                move_notification_to_archive(notify_id)
                print(f"Уведомление {notify_id} отправлено пользователю {user_id} и перемещено в архив")
            except Exception as e:
                print(f"Ошибка отправки уведомления {notify_id}: {e}")
        time.sleep(60)

threading.Thread(target=check_notifications, daemon=True).start()
