import socket
import threading
import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.constants import HOST, PORT, BUFFER_SIZE

clients = {}      # socket -> username
usernames = set() # active usernames

def broadcast(message, sender_socket=None):
    for client_socket in clients:
        try:
            client_socket.send(message.encode())
        except:
            client_socket.close()


def broadcast_user_list():
    user_list_msg = "__USER_LIST__:" + json.dumps(list(usernames))
    for client_socket in clients:
        try:
            client_socket.send(user_list_msg.encode())
        except:
            pass

def handle_client(client_socket):
    try:
        username = client_socket.recv(BUFFER_SIZE).decode()
        if username in usernames:
            client_socket.send("__USERNAME_TAKEN__".encode())
            client_socket.close()
            return

        clients[client_socket] = username
        usernames.add(username)
        broadcast(f"(System): {username} has joined the chat!")
        broadcast_user_list()

        while True:
            msg = client_socket.recv(BUFFER_SIZE).decode()
            if not msg:
                break
            if msg.startswith("/w"):
                try:
                    _, recipient, content = msg.split(" ", 2)
                    found = False
                    for sock, user in clients.items():
                        if user == recipient:
                            sock.send(f"(Private) ({username}): {content}".encode())
                            client_socket.send(f"(Private) ({username} to {recipient}): {content}".encode())
                            found = True
                            break
                    if not found:
                        client_socket.send(f"(System): User '{recipient}' not found.".encode())
                # except:
                #     client_socket.send("(System): Invalid private message format.".encode())
                except ValueError:
                    client_socket.send("(System): Invalid private message format. Use: /w username message".encode())
            else:
                broadcast(f"(Global) ({username}): {msg}", sender_socket=None)
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if client_socket in clients:
            left_user = clients.pop(client_socket)
            usernames.remove(left_user)
            broadcast(f"(System): {left_user} has left the chat.")
            broadcast_user_list()
            client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[SERVER RUNNING] {HOST}:{PORT}")
    while True:
        client_socket, addr = server.accept()
        print(f"[NEW CONNECTION] {addr}")
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

if __name__ == "__main__":
    start_server()
