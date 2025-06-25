from flask import Flask, render_template_string
import socketio
import sys
import os
import base64

# Add parent directory to path for module import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class ChatServer:
    def __init__(self):
        # Initialize Flask and Socket.IO
        self.sio = socketio.Server()
        self.app = Flask(__name__)
        self.app.wsgi_app = socketio.WSGIApp(self.sio, self.app.wsgi_app)

        # In-memory state
        self.users = []          # Connected users: list of {'sid', 'username', 'aes_key'}
        self.aes_keys = {}       # Temporary AES key store: sid -> aes_key
        self.private_key = load_rsa_private_key("private_key.pem")  # Load RSA private key

        self.setup_routes()
        self.register_events()

    def setup_routes(self):
        # Simple landing page
        INDEX_HTML = '''
        <!DOCTYPE html>
        <html>
        <head><title>Chat</title></head>
        <body><h1>Secure Chat Server</h1></body>
        </html>
        '''
        @self.app.route('/')
        def index():
            return render_template_string(INDEX_HTML)

    def register_events(self):
        # --- Connection lifecycle ---

        @self.sio.event
        def connect(sid, environ):
            print(f"Client connected: {sid}")

        @self.sio.event
        def disconnect(sid):
            # Handle disconnect: remove user and notify others
            username = None
            for user in self.users:
                if user['sid'] == sid:
                    username = user['username']
                    break
            self.users = [user for user in self.users if user['sid'] != sid]
            self.aes_keys.pop(sid, None)
            usernames = [user['username'] for user in self.users]

            if username:
                print(f"User {username} disconnected ({sid})")
                self.sio.emit('user_left', {'username': username, 'usernames': usernames})
            else:
                print(f"Client disconnected: {sid}")
                self.sio.emit('user_left', {'username': 'Unknown', 'usernames': usernames})

        # --- Key exchange and user join/leave ---

        @self.sio.event
        def exchange_key(sid, data):
            # Decrypt and store AES key sent by client
            encrypted_aes_b64 = data.get('encrypted_aes')
            encrypted_aes = base64.b64decode(encrypted_aes_b64.encode())
            try:
                aes_key = decrypt_rsa(self.private_key, encrypted_aes)
                self.aes_keys[sid] = aes_key
                print(f"[Key Exchange] AES key received for client {sid}")
            except Exception as e:
                print(f"[Key Exchange] Failed: {e}")

        @self.sio.event
        def user_joined(sid, data):
            # Finalize user join by binding username with sid and AES key
            username = data.get('username', 'Unknown')
            aes_key = self.aes_keys.pop(sid, None)
            self.users.append({'sid': sid, 'username': username, 'aes_key': aes_key})
            usernames = [user['username'] for user in self.users]
            print(f"User {username} joined with session ID {sid}")
            self.sio.emit('user_joined', {'username': username, 'usernames': usernames})

        @self.sio.event
        def user_left(sid, data):
            # Remove user from list on leave event
            username = data.get('username', 'Unknown')
            self.users[:] = [user for user in self.users if user['sid'] != sid]
            usernames = [user['username'] for user in self.users]
            print(f"User {username} left with session ID {sid}")
            self.sio.emit('user_left', {'username': username, 'usernames': usernames})
            self.aes_keys.pop(sid, None)

        # --- Messaging ---

        @self.sio.event
        def global_message(sid, data):
            # Receive AES-encrypted global message, decrypt, re-encrypt for each user
            sender = data.get('sender', 'Anonymous')
            ciphertext = data.get('message', '')
            sender_entry = next((u for u in self.users if u['sid'] == sid), None)

            if not sender_entry:
                print("Sender not found.")
                return

            try:
                plaintext = decrypt_aes(sender_entry['aes_key'], ciphertext)
                print(f"[GLOBAL] From {sender}: {ciphertext}")
            except Exception as e:
                print(f"Failed to decrypt sender's message: {e}")
                return

            for user in self.users:
                try:
                    re_encrypted = encrypt_aes(user['aes_key'], plaintext)
                    self.sio.emit('incoming_global_message', {'message': re_encrypted, 'sender': sender}, room=user['sid'])
                except Exception as e:
                    print(f"Failed to re-encrypt for {user['username']}: {e}")

        @self.sio.event
        def private_message(sid, data):
            # Receive AES-encrypted private message, re-encrypt for specific recipient
            recipient_name = data.get('recipient', '')
            ciphertext = data.get('message', '')
            sender = data.get('sender', 'Anonymous')

            sender_entry = next((u for u in self.users if u['sid'] == sid), None)
            recipient_entry = next((u for u in self.users if u['username'] == recipient_name), None)

            if not sender_entry or not recipient_entry:
                print("Sender or recipient not found.")
                return

            try:
                plaintext = decrypt_aes(sender_entry['aes_key'], ciphertext)
                print(f"[PRIVATE] From {sender} to {recipient_name}: {ciphertext}")
                re_encrypted = encrypt_aes(recipient_entry['aes_key'], plaintext)
                self.sio.emit('incoming_private_message', {'message': re_encrypted, 'sender': sender}, room=recipient_entry['sid'])
            except Exception as e:
                print(f"Failed private message forwarding: {e}")

        # --- User info ---

        @self.sio.event
        def get_current_users(sid):
            # Return current list of usernames
            usernames = [user['username'] for user in self.users]
            return {'current_usernames': usernames}

# --- Entry Point ---
if __name__ == '__main__':
    server = ChatServer()
    server.app.run(port=8080, debug=True)