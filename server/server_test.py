from flask import Flask, render_template_string
import socketio

sio = socketio.Server()
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

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

@sio.event
def chat_message(sid, data):
    print("Message received:", data)
    message = data.get('message', '')
    sender = data.get('sender', 'Anonymous')
    sio.emit('incoming_message', {'message': message, 'sender': sender})

@sio.event
def disconnect(sid):
    print('Client disconnected:', sid)

if __name__ == '__main__':
    app.run(port=8080)
