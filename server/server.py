import socketio
import sys
import os
import base64
import eventlet
import hashlib

from flask import Flask, render_template_string
from crypto_utils import load_rsa_private_key, decrypt_rsa, decrypt_aes, encrypt_aes

# Add parent directory to path for module import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logs.db_logger import log_event

# File
UPLOAD_FOLDER = "upload_files"
CHUNK_SIZE = 49152 # 48KB 
os.makedirs(UPLOAD_FOLDER, exist_ok = True)

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

        # File transfer
        self.upload_files = {}
        
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
            log_event("server", "connect", f"Client {sid} connected.")

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
                log_event("server", "disconnect", f"User {username} disconnected ({sid})")
                self.sio.emit('user_left', {'username': username, 'usernames': usernames})
            else:
                print(f"Client disconnected: {sid}")
                log_event("server", "disconnect", f"Client disconnected: {sid}")
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
                log_event("server", "exchange_key", f"[Key Exchange] AES key received for client {sid}")
            except Exception as e:
                print(f"[Key Exchange] Failed: {e}")
                log_event("server", "exchange_key_failed", f"[Key Exchange] Failed: {e}")

        @self.sio.event
        def user_joined(sid, data):
            # Finalize user join by binding username with sid and AES key
            username = data.get('username', 'Unknown')
            aes_key = self.aes_keys.pop(sid, None)
            self.users.append({'sid': sid, 'username': username, 'aes_key': aes_key})
            usernames = [user['username'] for user in self.users]
            print(f"User {username} joined with session ID {sid}")
            log_event("server", "user_joined", f"User '{username}' joined (SID: {sid})")
            self.sio.emit('user_joined', {'username': username, 'usernames': usernames})

        @self.sio.event
        def user_left(sid, data):
            # Remove user from list on leave event
            username = data.get('username', 'Unknown')
            self.users[:] = [user for user in self.users if user['sid'] != sid]
            usernames = [user['username'] for user in self.users]
            print(f"User {username} left with session ID {sid}")
            log_event("server", "user_left", f"User {username} left with session ID {sid}")
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
                log_event("server", "global_msg", "Sender not found.")
                return

            try:
                plaintext = decrypt_aes(sender_entry['aes_key'], ciphertext)
                print(f"[GLOBAL] From {sender}: {ciphertext}")
                log_event("server", "global_msg", f"[GLOBAL] From {sender}: {ciphertext}")
            except Exception as e:
                print(f"Failed to decrypt sender's message: {e}")
                log_event("server", "global_msg", f"Failed to decrypt sender's message: {e}")
                return

            for user in self.users:
                try:
                    re_encrypted = encrypt_aes(user['aes_key'], plaintext)
                    self.sio.emit('incoming_global_message', {'message': re_encrypted, 'sender': sender}, room=user['sid'])
                except Exception as e:
                    print(f"Failed to re-encrypt for {user['username']}: {e}")
                    log_event("server", "global_msg", f"Failed to re-encrypt for {user['username']}: {e}")

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
                log_event("server", "private_msg", "Sender or recipient not found.")
                return

            try:
                plaintext = decrypt_aes(sender_entry['aes_key'], ciphertext)
                print(f"[PRIVATE] From {sender} to {recipient_name}: {ciphertext}")
                log_event("server", "private_msg", f"[PRIVATE] From {sender} to {recipient_name}: {ciphertext}")
                re_encrypted = encrypt_aes(recipient_entry['aes_key'], plaintext)
                self.sio.emit('incoming_private_message', {'message': re_encrypted, 'sender': sender}, room=recipient_entry['sid'])
            except Exception as e:
                print(f"Failed private message forwarding: {e}")
                log_event("server", "private_msg", f"Failed private message forwarding: {e}")

        # --- User info ---
        @self.sio.event
        def get_current_users(sid):
            # Return current list of usernames
            usernames = [user['username'] for user in self.users]
            return {'current_usernames': usernames}
        
        # --- File transfer: Public & Private ---
        @self.sio.event
        def start_upload(sid, data):
            filename = data.get('filename', '')
            sender = data.get('sender', 'Anonymous')
            recipient = data.get('recipient', 'Global')
            
            if not recipient:
                print("Recipient not found.")
                log_event("server", "start_upload", "Recipient not found.")
                return

            path = os.path.join(UPLOAD_FOLDER, filename)

            try:
                file = open(path, 'wb')
                hash_algo = hashlib.sha256()
                
                # self.upload_files[(sid, filename, recipient)] = file  # Track the file by sid
                self.upload_files[(sid, filename, recipient)] = {"file": file, 
                                                                 "hash_compare": hash_algo}
                
                print(f"[Upload from {sender} to Server] Start: {filename}")
                log_event("server", "start_upload", f"Start upload: {filename} from {sender} to {recipient}")
            except Exception as e:
                print(f"[start_upload] Failed to create file: {e}")
                log_event("server", "start_upload", f"Failed to create file: {e}")
                
        # Send checks
        @self.sio.event
        def upload_chunk(sid, data):
            # Decode the base64 to binary when server receives the chunks
            chunk = base64.b64decode(data.get('chunk_data', None))
            filename = data.get('filename', '')
            recipient = data.get('recipient', 'Global')
            
            file_info = self.upload_files.get((sid, filename, recipient))
            if not file_info:
                return
            
            file = file_info['file']
            hash_compare = file_info['hash_compare']
            
            if file:
                try:
                    file.write(chunk) # Write in the received file
                    hash_compare.update(chunk)
                    # print(f"[upload_chunk] Chunk received: {filename}")
                    # file['content'].write(chuck)
                except Exception as e:
                    print(f"[upload_chunk] Failed to write chunk")
                    log_event("server", "upload_chunk_failed", f"Failed to write chunk for {filename}: {e}")
                    
        # Finish uploading file
        @self.sio.event
        def finish_upload(sid, data):
            filename = data.get('filename', '')
            sender = data.get('sender', 'Anonymous')
            recipient = data.get('recipient', 'Global')
            client_hash = data.get('hash_file', '')
            timestamp = data.get('time', '')
                
            file_info = self.upload_files.get((sid, filename, recipient))
            if not file_info:
                return
            
            try: 
                file_info['file'].close()
                computed_hash = file_info['hash_compare'].hexdigest()
                
                if computed_hash != client_hash:
                    print(f"[finish_upload] Hash mismatch: expected {client_hash}, got {computed_hash}")
                    log_event("server", "finish_upload_failed", f"Hash mismatch for {filename}")
                    
                    # Construct full path to the file
                    file_path = os.path.join(UPLOAD_FOLDER, filename)  # Replace UPLOAD_FOLDER with your actual directory variable
                    
                    # # Delete the failed file
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"[finish_upload] Deleted corrupt file: {file_path}")
                        log_event("server", "delete_failed_upload_file", f"Deleted corrupt file: {file_path}")
                                    
                    self.sio.emit('retry_sending', {
                        'filename': filename,
                        'sender': sender
                    })
                    return
                
                print(f"[Upload from {sender} to Server] Finished upload {filename}")
                log_event("server", "finish_upload", f"Finished upload: {filename} from {sender} to {recipient} at {timestamp}")
                
                if recipient == "Global":
                    for user in self.users:
                        # Notify 'incoming_global_file' to all users
                        # Global file
                        self.sio.emit('incoming_global_file', {
                                      'filename': filename,
                                      'sender': sender,
                                      'time': timestamp
                        }, room=user['sid'])
                else:
                    recipient_entry = next((u for u in self.users if u['username'] == recipient), None)
                    
                    self.sio.emit('incoming_private_file', {
                                  'filename': filename,
                                  'sender': sender,
                                  'time': timestamp
                    }, room=recipient_entry['sid'])    
                                
            except Exception as e:
                print(f"[finish_upload] Failed to finalize file")
                log_event("server", "finish_upload_failed", f"Failed to finalize file {filename}: {e}")
            finally:
                self.upload_files.pop((sid, filename, recipient), None)
                        
        # --- Request download file --- 
        @self.sio.event
        def download_request(sid, data):
            filename = data.get('filename', '')
            path = os.path.join(UPLOAD_FOLDER, filename)
            hash_algo_download = hashlib.sha256()
            
            if not os.path.exists(path):
                print(f"[download_request] File not found: {filename}")
                log_event("server", "download_request_failed", f"File not found: {filename}")
                return

            print(f"Start to downloading {filename}")
            # Send chunks to receiver
            def send_chunks():
                try:
                    with open(path, 'rb') as file:
                        while True:
                            chunk = file.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            hash_algo_download.update(chunk)
                            
                            encoded_data = base64.b64encode(chunk).decode()
                            self.sio.emit('incoming_file_chunk', {
                                    'chunk_data': encoded_data,
                                    'filename': filename}, 
                                    room=sid)
                            
                    self.sio.emit('finish_download', {'filename': filename, 'hash_file': hash_algo_download.hexdigest()}, room=sid)
                except Exception as e:
                    print(f"[send_chunks] Failed to send file: {e}")
                    log_event("server", "send_chunks_failed", f"Failed to send file {filename}: {e}")
            
            self.sio.start_background_task(send_chunks)
        
# --- Entry Point ---
if __name__ == '__main__':
    server = ChatServer()
    # server.app.run(port=8080, debug=True)
    eventlet.wsgi.server(eventlet.listen(('localhost', 8080)), server.app)