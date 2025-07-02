import telebot
from config import TOKEN
from handlers import register_handlers
from database import connect_to_mssql
from web_server import run_web_server
from scheduler import check_notifications
from threading import Thread

bot = telebot.TeleBot(TOKEN)
register_handlers(bot)

if __name__ == "__main__":
    # Проверка подключения к БД
    if connect_to_mssql():
        print("✅ Подключение к БД успешно")
    else:
        print("❌ Ошибка подключения к БД")

    # Запускаем веб-сервер в отдельном потоке
    Thread(target=run_web_server, daemon=True).start()
    # Запускаем планировщик уведомлений в отдельном потоке
    Thread(target=check_notifications, daemon=True).start()
    print("🤖Бот запущен...")
    bot.polling(none_stop=True)