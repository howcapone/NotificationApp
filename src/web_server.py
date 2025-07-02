import flask
from flask import Flask, request, render_template
import threading
from database import create_notification
from config import WEB_SERVER_URL
from datetime import datetime
app = Flask(__name__, template_folder='templates')

@app.route('/form/<int:user_id>')
def show_form(user_id):
    return render_template('notification_form.html',
                           user_id=user_id,
                           web_server_url=WEB_SERVER_URL)


@app.route('/api/create_notification', methods=['POST'])
def api_create_notification():
    try:
        data = request.json
        if not data or 'user_id' not in data or 'text' not in data or 'time' not in data:
            return {"status": "error", "message": "Недостаточно данных"}, 400

        time_str = data['time']
        try:
            dt_obj = datetime.strptime(time_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            return {"status": "error", "message": "Неверный формат времени"}, 400

        notification_id = create_notification(
            user_id=data['user_id'],
            text=data['text'],
            notify_time=dt_obj,
        )

        if notification_id:
            return {
                "status": "success",
                "notification_id": notification_id,
                "message": "Уведомление успешно создано"
            }, 200

        return {"status": "success", "message": "Уведомление успешно создано!"}, 400

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

def run_web_server():
    app.run(host='0.0.0.0', port=5000)
