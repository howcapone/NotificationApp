from telebot import types

def register_handlers(bot):
    @bot.message_handler(commands=["start"])
    def send_welcome(message):
        bot.reply_to(message, "Привет! Я бот для уведомлений. Используй /help.")

    @bot.message_handler(commands=["help"])
    def send_help(message):
        bot.reply_to(message, "Доступные команды: /start, /help")