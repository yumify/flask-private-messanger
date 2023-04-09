from datetime import datetime

import pymongo
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'segs'
socketio = SocketIO(app)

client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["mydatabase"]
collection = db["messages"]

last_message = collection.find_one(sort=[("_id", pymongo.DESCENDING)])
message_id = last_message['_id'] + 1 if last_message else 0


@app.template_filter('datetimeformat')
def datetimeformat(value):
    now = datetime.now()
    date_time = datetime.strptime(value, '%d-%m-%Y %H:%M:%S')
    diff = now - date_time
    if diff.days == 0 and diff.seconds < 86400:
        if now.day == date_time.day:
            return 'Сегодня в ' + date_time.strftime('%H:%M')
        else:
            return 'Вчера в ' + date_time.strftime('%H:%M')
    else:
        return date_time.strftime('%d-%m-%Y в %H:%M')


@app.route('/<sender>/<recipient>')
def index(sender, recipient):
    incoming_messages = list(collection.find({'sender': recipient, 'recipient': sender}))
    outcoming_messages = list(collection.find({'sender': sender, 'recipient': recipient}))
    messages = incoming_messages + outcoming_messages
    messages.sort(key=lambda x: x.get('timestamp', x['_id']))
    app.logger.info(messages)
    return render_template('index.html', messages=messages, sender=sender, recipient=recipient)


@socketio.on('connect')
def handle_connect():
    messages = list(collection.find())
    emit('messages', messages)


@socketio.on('send_message')
def handle_send_message(data):
    global message_id
    current_datetime = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    message = {
        '_id': message_id,
        'sender': data[0],
        'recipient': data[1],
        'message': data[2],
        'date_time': f'{current_datetime}'
    }
    message_id += 1
    collection.insert_one(message)

    if data[0] and data[1]:
        emit('new_message', message, broadcast=True)
        print(message)


if __name__ == '__main__':
    # socketio.run(app, allow_unsafe_werkzeug=True)
    app.jinja_env.cache = {}
    socketio.run(app, allow_unsafe_werkzeug=True, host='0.0.0.0', port=80)
