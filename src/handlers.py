import bcrypt
from telebot import types
from datetime import datetime, timedelta
from database import (
    register_or_verify_user,
    check_user_exists,
    get_user_notifications,
    get_user_archive,
    delete_notification_by_id,
    delete_archive_by_notify_id,
    get_notification_by_id,
    update_notification_text,
    update_notification_time,
    restore_from_archive,
    get_archive_item_by_id
)
from config import WEB_SERVER_URL


def register_handlers(bot):
    @bot.message_handler(commands=['start'])
    def handle_start(message):
        user_id = message.from_user.id
        username = message.from_user.username or f"user_{user_id}"
        if check_user_exists(user_id):
            show_main_menu(bot, message)
        else:
            request_password(bot, message, user_id, username)

    @bot.message_handler(commands=['help'])
    def handle_help(message):
        help_text = (
            "🛠 *Помощь по боту*\n\n"
            "Я помогу вам не пропустить важные события!\n\n"
            "🔹 */start* - начать работу с ботом\n"
            "🔹 */help* - показать это сообщение\n\n"
            "Используйте кнопки меню для управления уведомлениями"
        )
        bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

    @bot.message_handler(func=lambda m: m.text == "📝 Создать уведомление")
    def handle_create_notification(message):
        user_id = message.from_user.id
        if check_user_exists(user_id):
            show_notification_form(bot, message, user_id)
        else:
            bot.send_message(message.chat.id, "🔒 Сначала авторизуйтесь через /start")

    @bot.message_handler(func=lambda m: m.text == "📋 Мои уведомления")
    def handle_view_notifications(message):
        user_id = message.from_user.id
        if not check_user_exists(user_id):
            bot.send_message(message.chat.id, "🔒 Сначала авторизуйтесь через /start")
            return

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton("🔄 Активные"),
            types.KeyboardButton("🗃 Архив"),
            types.KeyboardButton("🔙 Назад")
        )
        bot.send_message(message.chat.id, "📂 Выберите раздел уведомлений:", reply_markup=markup)

    @bot.message_handler(func=lambda m: m.text == "🔄 Активные")
    def handle_active_notifications(message):
        user_id = message.from_user.id
        notifications = get_user_notifications(user_id)

        if not notifications:
            bot.send_message(message.chat.id, "📭 У вас нет активных уведомлений.")
            return

        for notify_id, text, notify_time in notifications:
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_edit = types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{notify_id}")
            btn_delete = types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_active_{notify_id}")
            markup.add(btn_edit, btn_delete)

            bot.send_message(
                message.chat.id,
                f"⏰ *{notify_time.strftime('%d.%m.%Y %H:%M')}*\n{text}",
                parse_mode='Markdown',
                reply_markup=markup
            )

    @bot.message_handler(func=lambda m: m.text == "🗃 Архив")
    def handle_archive_notifications(message):
        user_id = message.from_user.id
        archive_items = get_user_archive(user_id)

        if not archive_items:
            bot.send_message(message.chat.id, "📭 Ваш архив уведомлений пуст.")
            return

        for notify_id, text, notify_time, send_id in archive_items:
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_restore = types.InlineKeyboardButton("🔄 Повторить", callback_data=f"restore_{send_id}")
            btn_delete = types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_archive_{send_id}")
            markup.add(btn_restore, btn_delete)

            bot.send_message(
                message.chat.id,
                f"⏰ *{notify_time.strftime('%d.%m.%Y %H:%M')}*\n{text}",
                parse_mode='Markdown',
                reply_markup=markup
            )

    @bot.message_handler(func=lambda m: m.text == "🔙 Назад")
    def handle_back(message):
        show_main_menu(bot, message)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete_active_'))
    def handle_delete_active(call):
        notify_id = int(call.data.split('_')[2])
        if delete_notification_by_id(notify_id):
            bot.answer_callback_query(call.id, "Уведомление удалено.")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Ошибка при удалении.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('delete_archive_'))
    def handle_delete_archive(call):
        send_id = int(call.data.split('_')[2])
        if delete_archive_by_notify_id(send_id):
            bot.answer_callback_query(call.id, "Уведомление удалено из архива.")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Ошибка при удалении.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('restore_'))
    def handle_restore_notification(call):
        send_id = int(call.data.split('_')[1])
        new_notify_id = restore_from_archive(send_id)

        if new_notify_id:
            bot.answer_callback_query(call.id, "Уведомление восстановлено и запланировано на завтра!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Ошибка при восстановлении уведомления.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('edit_') and
                                                  not call.data.startswith('edit_text_') and
                                                  not call.data.startswith('edit_time_'))
    def handle_edit_notification(call):
        notify_id = int(call.data.split('_')[1])
        notification = get_notification_by_id(notify_id)

        if not notification:
            bot.answer_callback_query(call.id, "Уведомление не найдено!")
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✏️ Текст", callback_data=f"edit_text_{notify_id}"),
            types.InlineKeyboardButton("⏰ Время", callback_data=f"edit_time_{notify_id}"),
            types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_active_{notify_id}"),
            types.InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_edit_{notify_id}")
        )

        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('edit_text_'))
    def handle_edit_text(call):
        notify_id = int(call.data.split('_')[2])
        bot.answer_callback_query(call.id, "Введите новый текст")
        bot.delete_message(call.message.chat.id, call.message.message_id)

        msg = bot.send_message(call.message.chat.id, "✏️ Введите новый текст уведомления:")
        bot.register_next_step_handler(msg, lambda m: process_text_step(m, notify_id))

    def process_text_step(message, notify_id):
        if update_notification_text(notify_id, message.text):
            notification = get_notification_by_id(notify_id)
            if notification:
                bot.send_message(
                    message.chat.id,
                    f"✅ Текст обновлен:\n⏰ {notification[2].strftime('%d.%m.%Y %H:%M')}\n📝 {message.text}",
                    parse_mode='Markdown'
                )
            else:
                bot.send_message(message.chat.id, "❌ Уведомление не найдено")
        else:
            bot.send_message(message.chat.id, "❌ Не удалось обновить текст")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('edit_time_'))
    def handle_edit_time(call):
        notify_id = int(call.data.split('_')[2])
        bot.answer_callback_query(call.id, "Введите новое время")
        bot.delete_message(call.message.chat.id, call.message.message_id)

        msg = bot.send_message(
            call.message.chat.id,
            "⏰ Введите новое время в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 31.12.2023 23:59"
        )
        bot.register_next_step_handler(msg, lambda m: process_time_step(m, notify_id))

    def process_time_step(message, notify_id):
        try:
            new_time = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
            if update_notification_time(notify_id, new_time):
                notification = get_notification_by_id(notify_id)
                if notification:
                    bot.send_message(
                        message.chat.id,
                        f"✅ Время обновлено:\n⏰ {new_time.strftime('%d.%m.%Y %H:%M')}\n📝 {notification[1]}",
                        parse_mode='Markdown'
                    )
                else:
                    bot.send_message(message.chat.id, "❌ Уведомление не найдено")
            else:
                bot.send_message(message.chat.id, "❌ Не удалось обновить время")
        except ValueError:
            bot.send_message(message.chat.id, "❌ Неверный формат! Используйте ДД.ММ.ГГГГ ЧЧ:ММ")
            bot.register_next_step_handler(message, lambda m: process_time_step(m, notify_id))

    @bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_edit_'))
    def handle_cancel_edit(call):
        notify_id = int(call.data.split('_')[2])
        bot.answer_callback_query(call.id, "Редактирование отменено")

        notification = get_notification_by_id(notify_id)
        if notification:
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_edit = types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{notify_id}")
            btn_delete = types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_active_{notify_id}")
            markup.add(btn_edit, btn_delete)

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"⏰ *{notification[2].strftime('%d.%m.%Y %H:%M')}*\n{notification[1]}",
                reply_markup=markup,
                parse_mode='Markdown'
            )


def request_password(bot, message, user_id, username):
    msg = bot.send_message(message.chat.id, "🔒 Введите пароль для доступа к боту:")
    bot.register_next_step_handler(msg, lambda m: check_password(bot, m, user_id, username))


def check_password(bot, message, user_id, username):
    from config import PASSWORD_HASH
    try:
        user_input = message.text.encode('utf-8')
        if bcrypt.checkpw(user_input, PASSWORD_HASH):
            if register_or_verify_user(user_id, username):
                bot.send_message(
                    message.chat.id,
                    "✅ *Авторизация успешна!*\n🚀 Добро пожаловать в NotificationAPP! Я помогу вам отслеживать важные события и напомню о них заранее. ",
                    parse_mode='Markdown'
                )
                show_main_menu(bot, message)
            else:
                bot.send_message(message.chat.id, "❌ Ошибка регистрации. Попробуйте позже.")
        else:
            bot.send_message(message.chat.id, "❌ Неверный пароль! Попробуйте снова.")
            request_password(bot, message, user_id, username)
    except Exception as e:
        print(f"Ошибка проверки пароля: {e}")
        bot.send_message(message.chat.id, "❌ Ошибка системы. Попробуйте позже.")


def show_notification_form(bot, message, user_id):
    web_app = types.WebAppInfo(url=f"{WEB_SERVER_URL}/form/{user_id}")
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_web = types.KeyboardButton("📝 Заполнить форму", web_app=web_app)
    btn_back = types.KeyboardButton("🔙 Назад")
    markup.add(btn_web, btn_back)
    bot.send_message(
        message.chat.id,
        "📋 Для создания уведомления нажмите кнопку ниже:",
        reply_markup=markup
    )


def show_main_menu(bot, message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📝 Создать уведомление"),
        types.KeyboardButton("📋 Мои уведомления")
    )
    bot.send_message(
        message.chat.id,
        "📱 *Главное меню*",
        reply_markup=markup,
        parse_mode='Markdown'
    )