import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to server")

@sio.event
def incoming_message(data):
    print("Message received:", data['message'])

@sio.event
def disconnect():
    print("Disconnected from server")

def main():
    try:
        sio.connect('http://localhost:8080')
        print("Connected. Type 'quit' to exit.")
        while True:
            message = input("You: ").strip()
            if message.lower() == 'quit':
                break
            if message:
                sio.emit('chat_message', {'message': message})
    except Exception as e:
        print("Connection error:", e)
    finally:
        sio.disconnect()

if __name__ == '__main__':
    main()
