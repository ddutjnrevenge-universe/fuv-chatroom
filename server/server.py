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
    users.append({'username': username, 'sid': sid})
    usernames = [user['username'] for user in users]
    print(f'User {username} joined with session ID {sid}')
    sio.emit('user_joined', {'username': username, 'users': usernames})

@sio.event
def user_left(sid, data):
    username = data.get('username', 'Unknown')
    # Remove user from the list
    users[:] = [user for user in users if user['sid'] != sid]
    usernames = [user['username'] for user in users]
    print(f'User {username} left with session ID {sid}')
    sio.emit('user_left', {'username': username, 'users': usernames})

@sio.event
def disconnect(sid):
    print('Client disconnected:', sid)

@sio.event
def global_message(sid, data):
    print("Message received:", data)
    message = data.get('message', '')
    sender = data.get('sender', 'Anonymous')
    sio.emit('incoming_global_message', {'message': message, 'sender': sender})

@sio.event
def private_message(sid, data):
    recipient_name = data.get('recipient', '')
    recipient_sid = None
    for user in users:
        if user['username'] == recipient_name:
            recipient_sid = user['sid']
            break

    message = data.get('message', '')
    sender = data.get('sender', 'Anonymous')
    if recipient_sid:
        print(f"Private message from {sender} to {recipient_sid}: {message}")
        sio.emit('incoming_private_message', {'message': message, 'sender': sender}, room=recipient_sid)
    else:
        print("No recipient specified for private message.")

if __name__ == '__main__':
    app.run(port=8080, debug=True)
