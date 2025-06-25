from flask import Flask, render_template_string
import socketio
import sys
import os
import base64
import eventlet

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from crypto_utils import load_rsa_private_key, decrypt_rsa, decrypt_aes, encrypt_aes

# Initialize Flask + SocketIO
sio = socketio.Server()
app = Flask(__name__)
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)

# User storage
users = []  # store connected users: {sid, username}
aes_keys = {}  # sid -> AES key

# File
UPLOAD_FOLDER = "upload_files"
CHUNK_SIZE = 4096 # 4 KB 
os.makedirs(UPLOAD_FOLDER, exist_ok = True)

# Tracking file: sid -> file object
upload_files = {}
# download_files = {}

# Load server private key
private_key = load_rsa_private_key("private_key.pem")

# Minimal landing page (optional)
INDEX_HTML = '''
    <!DOCTYPE html>
    <html>
    <head><title>Chat</title></head>
    <body>
        <h1>Secure Chat Server</h1>
    </body>
    </html>
'''

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

# Handle new connection
@sio.event
def connect(sid, environ):
    print(f"Client connected: {sid}")

# Exchange AES key securely from client
@sio.event
def exchange_key(sid, data):
    encrypted_aes_b64 = data.get('encrypted_aes')
    encrypted_aes = base64.b64decode(encrypted_aes_b64.encode())

    try:
        aes_key = decrypt_rsa(private_key, encrypted_aes)
        # Instead of updating aes_keys dict, we update user list directly later when username is received.
        # For now just temporarily store sid->aes_key map
        aes_keys[sid] = aes_key
        print(f"[Key Exchange] AES key received for client {sid}")
    except Exception as e:
        print(f"[Key Exchange] Failed: {e}")

# Handle user joining
@sio.event
def user_joined(sid, data):
    username = data.get('username', 'Unknown')
    aes_key = aes_keys.get(sid)
    users.append({'sid': sid, 'username': username, 'aes_key': aes_key})
    usernames = [user['username'] for user in users]
    print(f"User {username} joined with session ID {sid}")
    sio.emit('user_joined', {'username': username, 'usernames': usernames})

# Handle user leaving
@sio.event
def user_left(sid, data):
    username = data.get('username', 'Unknown')
    users[:] = [user for user in users if user['sid'] != sid]
    usernames = [user['username'] for user in users]
    print(f"User {username} left with session ID {sid}")
    sio.emit('user_left', {'username': username, 'usernames': usernames})
    aes_keys.pop(sid, None)  # Clean up AES key when user leaves

# Handle disconnect
@sio.event
def disconnect(sid):
    # for user in users:
    #     if user['sid'] == sid:
    #         username = user['username']
    #         users.remove(user)
    #         usernames = [user['username'] for user in users]
    #         sio.emit('user_left', {'username': username, 'usernames': usernames})
    #         print(f"User {username} disconnected with session ID {sid}")
    #         break
    # aes_keys.pop(sid, None)
    global users
    # Find the username associated with the sid
    username = None
    for user in users:
        if user['sid'] == sid:
            username = user['username']
            break

    users = [user for user in users if user['sid'] != sid]
    usernames = [user['username'] for user in users]

    if username:
        sio.emit('user_left', {'username': username, 'usernames': usernames})
        print(f"User {username} disconnected with session ID {sid}")
    else:
        sio.emit('user_left', {'username': 'Unknown', 'usernames': usernames})
        print(f"Client disconnected: {sid}")

    aes_keys.pop(sid, None)
    
    # Clean up incomplete/corrupted resources when a client disconnects 
    # if sid in upload_files:
    #     # Close the file
    #     upload_files[sid].close()
    #     # Remove the sid from the dictionary
    #     del upload_files[sid]
    # if sid in download_files:
    #     download_files[sid].close()
    #     del download_files[sid]

# Current active user list (optional)
@sio.event
def get_current_users(sid):
    usernames = [user['username'] for user in users]
    return {'current_usernames': usernames}

# Global message forwarding (AES already encrypted, just relay)
@sio.event
def global_message(sid, data):
    sender = data.get('sender', 'Anonymous')
    ciphertext = data.get('message', '')

    # Find sender's AES key
    sender_entry = next((u for u in users if u['sid'] == sid), None)
    if not sender_entry:
        print("Sender not found.")
        return

    try:
        plaintext = decrypt_aes(sender_entry['aes_key'], ciphertext)
        print(f"[GLOBAL] From {sender}: {ciphertext}")  

    except Exception as e:
        print(f"Failed to decrypt sender's message: {e}")
        return

    # Re-encrypt separately for each receiver
    for user in users:
        try:
            re_encrypted = encrypt_aes(user['aes_key'], plaintext)
            sio.emit('incoming_global_message', {'message': re_encrypted, 'sender': sender}, room=user['sid'])
        except Exception as e:
            print(f"Failed to re-encrypt for {user['username']}: {e}")

# Private message forwarding (AES already encrypted, just relay)
@sio.event
def private_message(sid, data):
    recipient_name = data.get('recipient', '')
    ciphertext = data.get('message', '')
    sender = data.get('sender', 'Anonymous')

    sender_entry = next((u for u in users if u['sid'] == sid), None)
    recipient_entry = next((u for u in users if u['username'] == recipient_name), None)

    if not sender_entry or not recipient_entry:
        print("Sender or recipient not found.")
        return

    try:
        plaintext = decrypt_aes(sender_entry['aes_key'], ciphertext)
        print(f"[PRIVATE] From {sender} to {recipient_name}: {ciphertext}")  
        re_encrypted = encrypt_aes(recipient_entry['aes_key'], plaintext)
        sio.emit('incoming_private_message', {'message': re_encrypted, 'sender': sender}, room=recipient_entry['sid'])
    except Exception as e:
        print(f"Failed private message forwarding: {e}")

# Start uploading file
# @sio.event
# def start_upload(sid, data):
#     filename = data.get('filename', '')
#     sender = data.get('sender', 'Anonymous')
#     receiver = data.get('receiver', 'global')
    
#     path = os.path.join(UPLOAD_FOLDER, filename)
    
#     try:
#         file = upload_files.get(sid)
#         if file:
#             file = open(path, 'wb')
#             # file_open = open(path, 'wb')
#             # file = {
#             #     'filename': filename,
#             #     'content': file_open, 
#             #     'sender': sender,
#             #     'receiver': receiver
#             # }
#             print(f"[Upload from {sender} to {receiver}] Start: {filename}")
#     except Exception as e:
#         print(f"[start_upload] Failed to create file: {e}")
@sio.event
def start_upload(sid, data):
    filename = data.get('filename', '')
    sender = data.get('sender', 'Anonymous')
    # receiver = data.get('receiver', 'global')

    path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        file = open(path, 'wb')
        upload_files[(sid, filename)] = file  # Track the file by sid
        print(f"[Upload from {sender} to Server] Start: {filename}")
    except Exception as e:
        print(f"[start_upload] Failed to create file: {e}")


# Send checks
@sio.event
def upload_chunk(sid, data):
    # Decode the base64 to binary when server receives the chunks
    chunk = base64.b64decode(data.get('chunk_data', None))
    filename = data.get('filename', '')
    
    file = upload_files.get((sid, filename))
    
    if file:
        try:
            file.write(chunk) # Write in the received file
            # print(f"[upload_chunk] Chunk received: {filename}")
            # file['content'].write(chuck)
        except Exception as e:
            print(f"[upload_chunk] Failed to write chunk")

# Finish uploading file
@sio.event
def finish_upload(sid, data):
    filename = data.get('filename', '')
    sender = data.get('sender', 'Anonymous')
    # receiver = data.get('receiver', 'global')
    timestamp = data.get('time', '')
        
    file = upload_files.get((sid, filename))
    if not file:
        return
    
    try: 
        file.close()
        
        print(f"[Upload from {sender} to Server] Finished upload {filename}")
        
        for user in users:
            # Notify 'file_ready' to all users
            # Global file
            sio.emit('file_ready', {
                    'filename': filename,
                    'sender': sender,
                    'time': timestamp
            }, room=user['sid'])
    except Exception as e:
        print(f"[finish_upload] Failed to finalize file")
    finally:
        upload_files.pop((sid, filename), None)

# Request download file
@sio.event
def download_request(sid, data):
    filename = data.get('filename', '')
    path = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(path):
        print(f"[download_request] File not found: {filename}")
        return

    # Send chunks to receiver
    def send_chunks():
        try:
            with open(path, 'rb') as file:
                while True:
                    chunk = file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    encoded_data = base64.b64encode(chunk).decode()
                    sio.emit('incoming_file_chunk', {
                             'chunk_data': encoded_data,
                             'filename': filename}, 
                             room=sid)
            sio.emit('finish_download', {'filename': filename}, room=sid)
        except Exception as e:
            print(f"[send_chunks] Failed to send file: {e}")
    
    sio.start_background_task(send_chunks)

# Run server
if __name__ == '__main__':
    # app.run(port=8080, debug=True)
    eventlet.wsgi.server(eventlet.listen(('localhost', 8080)), app)
