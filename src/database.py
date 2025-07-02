import pyodbc
from datetime import datetime, timedelta
from config import DB_CONFIG

def connect_to_mssql():
    server = "localhost\SQLEXPRESS"
    database = "NotificationAPP"

    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
        )
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return None


def register_or_verify_user(user_id, username):
    conn = connect_to_mssql()
    if conn:
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                print(f"Пользователь {user_id} уже существует")
                return True

            cursor.execute(
                "INSERT INTO users (user_id, username, user_role) VALUES (?, ?, 1)",
                (user_id, username)
            )
            conn.commit()
            print(f"✅ Пользователь {username} ({user_id}) успешно зарегистрирован")
            return True

        except Exception as e:
            print(f"❌ Ошибка регистрации пользователя: {e}")
            return False
        finally:
            conn.close()
    return False


def check_user_exists(user_id):
    conn = connect_to_mssql()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            print(f"❌ Ошибка проверки пользователя: {e}")
            return False
        finally:
            conn.close()
    return False


def create_notification(user_id, text, notify_time):
    conn = connect_to_mssql()
    if not conn:
        print("Не удалось подключиться к базе")
        return None
    try:
        cursor = conn.cursor()

        # Проверка, что notify_time не в прошлом
        now = datetime.now()
        if notify_time <= now:
            print("❌ Ошибка: Нельзя создавать уведомления в прошлом.")
            return None  # Прекращаем создание уведомления

        # Вставляем только текст, время и user_id
        cursor.execute(
            "INSERT INTO notification (text, time, user_id) VALUES (?, ?, ?)",
            (text, notify_time, user_id)
        )
        conn.commit()
        # Если по каким-то причинам не получилось получить ID, возвращаем None
        print(f"Успешное создание уведомления!")
    except Exception as e:
        print(f"❌ Ошибка создания уведомления: {e}")
    finally:
        conn.close()

def get_pending_notifications():
    conn = connect_to_mssql()
    if not conn:
        return []

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT n.notify_id, n.text, n.user_id 
            FROM notification n
            WHERE n.time <= GETDATE()
            AND NOT EXISTS (
                SELECT 1 FROM archive a 
                WHERE a.notify_id = n.notify_id
            )
        """)
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Ошибка получения уведомлений: {e}")
        return []
    finally:
        conn.close()


def mark_notification_answered(notify_id, user_id):
    conn = connect_to_mssql()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(answer_id) FROM answers")
            max_id = cursor.fetchone()[0] or 0
            new_id = max_id + 1

            cursor.execute(
                "INSERT INTO answers (answer_id, message_id, text, user_id) VALUES (?, ?, ?, ?)",
                (new_id, notify_id, "Уведомление доставлено", user_id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка отметки уведомления: {e}")
            return False
        finally:
            conn.close()
    return False


def move_notification_to_archive(notify_id):
    conn = connect_to_mssql()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT notify_id, text, time, user_id
                       FROM notification
                       WHERE notify_id = ?
                       """, (notify_id,))
        notification = cursor.fetchone()

        if not notification:
            print(f"❌ Уведомление {notify_id} не найдено")
            return False
        notify_id, text, notify_time, user_id = notification
        cursor.execute("SELECT ISNULL(MAX(send_id), 0) FROM archive")
        new_send_id = cursor.fetchone()[0] + 1
        cursor.execute("""
                       INSERT INTO archive (send_id, text, time, user_id, notify_id)
                       VALUES (?, ?, ?, ?, ?)
                       """, (new_send_id, text, notify_time, user_id, notify_id))
        cursor.execute("ALTER TABLE archive NOCHECK CONSTRAINT FK_archive_notification")
        cursor.execute("DELETE FROM notification WHERE notify_id = ?", (notify_id,))
        cursor.execute("ALTER TABLE archive CHECK CONSTRAINT FK_archive_notification")
        conn.commit()
        print(f"✅ Уведомление {notify_id} перемещено в архив как запись {new_send_id}")
        return True

    except Exception as e:
        print(f"❌ Критическая ошибка при перемещении уведомления {notify_id}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_user_notifications(user_id):
    conn = connect_to_mssql()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT notify_id, text, time FROM notification WHERE user_id = ? ORDER BY time",
                (user_id,)
            )
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Ошибка получения уведомлений: {e}")
            return []
        finally:
            conn.close()
    return []


def get_user_archive(user_id):
    conn = connect_to_mssql()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("""
                       SELECT a.notify_id, a.text, a.time, a.send_id
                       FROM archive a
                       WHERE a.user_id = ?
                       ORDER BY a.time DESC
                       """, (user_id,))
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Ошибка получения архива: {e}")
        return []
    finally:
        conn.close()


def delete_archive_by_notify_id(notify_id):
    conn = connect_to_mssql()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM archive WHERE send_id = ?", (notify_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка удаления из архива: {e}")
        return False
    finally:
        conn.close()


def delete_notification_by_id(notify_id):
    conn = connect_to_mssql()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notification WHERE notify_id = ?", (notify_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка удаления уведомления: {e}")
        return False
    finally:
        conn.close()


def get_notification_by_id(notify_id):
    conn = connect_to_mssql()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT notify_id, text, time FROM notification WHERE notify_id = ?",
            (notify_id,)
        )
        return cursor.fetchone()
    except Exception as e:
        print(f"❌ Ошибка получения уведомления: {e}")
        return None
    finally:
        conn.close()


def get_archive_item_by_id(send_id):
    conn = connect_to_mssql()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT send_id, text, time, user_id, notify_id FROM archive WHERE send_id = ?",
            (send_id,)
        )
        return cursor.fetchone()
    except Exception as e:
        print(f"❌ Ошибка получения элемента архива: {e}")
        return None
    finally:
        conn.close()


def update_notification_text(notify_id, new_text):
    conn = connect_to_mssql()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notification SET text = ? WHERE notify_id = ?",
            (new_text, notify_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка обновления текста: {e}")
        return False
    finally:
        conn.close()


def update_notification_time(notify_id, new_time):
    conn = connect_to_mssql()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE notification SET time = ? WHERE notify_id = ?",
            (new_time, notify_id)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка обновления времени: {e}")
        return False
    finally:
        conn.close()


def restore_from_archive(send_id):
    conn = connect_to_mssql()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        archive_item = get_archive_item_by_id(send_id)
        if not archive_item:
            return False
        send_id, text, time, user_id, notify_id = archive_item
        new_time = datetime.now() + timedelta(days=1)
        cursor.execute(
            "INSERT INTO notification (text, time, user_id) OUTPUT INSERTED.notify_id VALUES (?, ?, ?)",
            (text, new_time, user_id)
        )
        new_notify_id = cursor.fetchone()[0]
        cursor.execute("DELETE FROM archive WHERE send_id = ?", (send_id,))
        conn.commit()
        return new_notify_id
    except Exception as e:
        print(f"❌ Ошибка восстановления из архива: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()



