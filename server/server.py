from flask import Flask, render_template_string
import socketio

sio = socketio.Server()
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)
users = [] # List to store connected users

INDEX_HTML = '''
    <!DOCTYPE html>
    <html>
    <head><title>Chat</title></head>
    <body>
        <h1>Simple Chat Server</h1>
    </body>
    </html>
'''

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@sio.event
def connect(sid, environ):
    print('Client connected:', sid)
    # sio.emit('current_users', {'users': users}, room=sid)
    # print(environ)

@sio.event
def user_joined(sid, data):
    username = data.get('username', 'Unknown')
    users.append(username)
    print(f'User {username} joined with session ID {sid}')
    sio.emit('user_joined', {'username': username, 'users': users})

@sio.event
def user_left(sid, data):
    username = data.get('username', 'Unknown')
    if username in users:
        users.remove(username)
    print(f'User {username} left with session ID {sid}')
    sio.emit('user_left', {'username': username})

@sio.event
def disconnect(sid):
    print('Client disconnected:', sid)

@sio.event
def chat_message(sid, data):
    print("Message received:", data)
    message = data.get('message', '')
    sender = data.get('sender', 'Anonymous')
    sio.emit('incoming_message', {'message': message, 'sender': sender})


if __name__ == '__main__':
    app.run(port=8080, debug=True)
