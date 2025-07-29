# -*- coding: utf-8 -*-
import os
import base64
import threading
import socketio
import sys
import time
import math
import hashlib
from queue import Queue

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinter.ttk import Progressbar
from datetime import datetime
from emoji_dict import EMOJI_DICT

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logs.db_logger import log_event

from server.crypto_utils import (
    load_rsa_public_key, encrypt_rsa, generate_aes_key,
    encrypt_aes, decrypt_aes
)

# Load server private key
public_key = load_rsa_public_key("public_key.pem")

FONT = "Georgia"
SERVER_API_URL = "http://localhost:8080"
CHUNK_SIZE = 49152 # 48KB

is_connecting = False
connection_failed = False

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y - 10}')

def setup_window(window, title, width, height):
    window.title(title)
    window.resizable(True, True)  # Allow window to be resizable
    window.configure(width=width, height=height)
    center_window(window, width, height)

class ChatClientGUI:
    def __init__(self):
        self.Window = tk.Tk()
        self.Window.withdraw()

        self.emoji_window = None
        self.username = None
        self.active_users = []
        
        # setup the socket client
        self.sio = socketio.Client()
        self.setup_socketio()
        # self.connect_to_server()
        
        # set up file transfer
        self.download_files = {}
        self.progress_n_index = {}
        self.upload_confirmation = {}
        
        self.login_screen()
        self.Window.mainloop()

    def setup_socketio(self):
        @self.sio.event
        def connect():
            print("Connected to server.")
            log_event("client", "connect", "Connected to server.")

            # # After connection, generate AES key & exchange
            self.session_aes_key = generate_aes_key()
            encrypted_aes = encrypt_rsa(public_key, self.session_aes_key)
            encrypted_aes_b64 = base64.b64encode(encrypted_aes).decode()
            self.sio.emit('exchange_key', {'encrypted_aes': encrypted_aes_b64})

        @self.sio.event
        def current_users(data):
            usernames = data.get('usernames', [])
            print(f"Current usernames: {usernames}")
            log_event("client", "current_users", f"Received current users: {usernames}")
            self.active_users = usernames
            # self.update_user_list(users)

        @self.sio.event
        def user_joined(data):
            username = data.get("username", "Unknown")
            usernames = data.get("usernames", [])
            self.active_users = usernames

            # Check if chat_box exists
            if not hasattr(self, 'chat_box') or self.chat_box is None: 
                return
            
            self.display_system_message(f"{username} has joined the chat.")
            self.update_user_list(usernames[::-1])

        @self.sio.event
        def user_left(data):
            username = data.get("username", "Unknown")
            usernames = data.get("usernames", [])
            self.active_users = usernames
            self.update_user_list(usernames[::-1])
            self.display_system_message(f"{username} has left the chat.")

        @self.sio.event
        def disconnect():
            print("Disconnected from server.")
            log_event("client", "disconnect", "Disconnected from server.")
            self.display_system_message("Disconnected from server. Exitting...")
            self.Window.attributes("-disabled", True)
            self.Window.after(5000, self.force_exit)

        @self.sio.event
        def incoming_global_message(data):
            sender = data.get("sender", "Unknown")
            try:
                # decrypted = decrypt_message(data.get("message", ""))
                decrypted = decrypt_aes(self.session_aes_key, data.get("message", ""))

                timestamp, message = decrypted.split("|", 1)
                self.display_message("Global", sender, message, timestamp)
            except Exception as e:
                self.display_system_message(f"Failed to decrypt global message from {sender}")

        @self.sio.event
        def incoming_private_message(data):
            sender = data.get("sender", "Unknown")
            try:
                # decrypted = decrypt_message(data.get("message", ""))
                decrypted = decrypt_aes(self.session_aes_key, data.get("message", ""))
                timestamp, message = decrypted.split("|", 1)
                # self.display_message("Private", sender, message, timestamp)
                self.display_message("Private", f"From {sender}", message, timestamp)

            except Exception as e:
                self.display_system_message(f"Failed to decrypt private message from {sender}")
        
        @self.sio.event
        def incoming_global_file(data):
            sender = data.get("sender", "Unknown")
            filename = data.get("filename", "")
            timestamp = data.get("time", "")
            
            if sender == self.username:
                # self.success_display_file("Global", sender, filename, timestamp)
                # self.display_download_button(filename)
                pass
            else:
                self.receive_file("Global", f"From {sender}", filename, timestamp)
        
        @self.sio.event
        def incoming_private_file(data):
            sender = data.get("sender", "Unknown")
            filename = data.get("filename", "")
            timestamp = data.get("time", "")
            
            self.receive_file("Private", f"From {sender}", filename, timestamp)
        
        @self.sio.event
        def incoming_file_chunk(data):
            chunk_data = data.get("chunk_data")
            filename = data.get("filename", "")
            
            if chunk_data:
                self.download_files[filename]['queue'].put(chunk_data) # Append encoded data to queue
                        
        @self.sio.event
        def finish_download(data):
            time.sleep(0.5)
            filename = data.get("filename", "")
            server_hash = data.get("hash_file", "")
            
            if filename in self.download_files:
                computed_hash = self.download_files[filename]['computed_hash'].hexdigest()
                saving_path = self.download_files[filename]['path']
                
                if computed_hash != server_hash:
                    messagebox.showerror("Error", f"Failed to download file {filename} from server. Please download again.")
                    log_event("client", "finish_download_failed", f"Hash mismatch for {filename}")
                    
                    # Delete the failed file
                    if os.path.exists(saving_path):
                        os.remove(saving_path)
                        log_event("client", "delete_failed_download_file", f"Deleted corrupt file: {saving_path}")
                else:
                    self.download_files[filename]['queue'].put(None)
                    self.display_system_message(f"File {filename} has been successfully downloaded.")
        
        @self.sio.event
        def retry_sending(data):
            filename = data.get("filename", "")
            sender = data.get("sender", "Unknown")
            
            if sender == self.username:
                # Cancel success timer if it's still pending
                if filename in self.upload_confirmation:
                    self.root.after_cancel(self.upload_confirmation[filename])
                    self.upload_confirmation.pop(filename, None)
                
                # Display the error
                messagebox.showerror("Error", f"File upload to server failed for '{filename}'. Please try resending the file.")
                self.error_upload(filename)
    
    def connect_to_server(self):
        def connect():
            try:
                self.sio.connect(SERVER_API_URL)
                self.sio.wait()
            except Exception as e:
                print(f"Connection failed: {e}")
                log_event("client", "connect_to_server_error", f"Connection failed: {e}")
        threading.Thread(target=connect, daemon=True).start()

    def update_user_server(self):
        """Update the server with the current username."""
        if self.sio.connected:
            self.sio.emit('user_joined', {'username': self.username})
        else:
            messagebox.showerror("Error", "Not connected to server.")

    def validate_username(self, username):
        username = username.strip()

        current_users = self.sio.call('get_current_users').get('current_usernames', [])
        self.active_users = current_users

        if not self.sio.connected:
            messagebox.showerror("Error", "Not connected to server.")
            return False
        
        if not username:
            messagebox.showwarning("Warning", "Please input a username.")
            return False
        elif len(username) > 9:
            messagebox.showwarning("Warning", "Username is too long. Please use a shorter username.")
            return False
        elif username.count(" ") > 0:
            messagebox.showwarning("Warning", "Username cannot contain spaces. Please choose another one.")
            return False
        elif not username.isalnum():
            messagebox.showwarning("Warning", "Username cannot contain special characters. Please choose another one.")
            return False
        elif username in self.active_users:
            messagebox.showwarning("Warning", "This username is already taken. Please choose another one.")
            return False
    
        self.username = username
        self.chatroom_screen()

        return True

    def setup_login_screen(self):
        self.login = tk.Toplevel(bg="midnight blue")
        setup_window(self.login, "FUV Chatroom Login", 680, 230)
        
        # Initialize frames
        content_frame = tk.Frame(self.login, bg="midnight blue")
        content_frame.place(relx=0.5, rely=0.45, anchor="center")
        
        left_frame = tk.Frame(content_frame, bg="midnight blue")
        left_frame.grid(row=0, column=0, padx=(0, 25), sticky="e")

        right_frame = tk.Frame(content_frame, bg="midnight blue")
        right_frame.grid(row=0, column=1, sticky="w")
        
        # Left side: Title
        title_text1 = tk.Label(left_frame, text="Welcome to", font=(FONT, 24), fg="white", bg="midnight blue")
        title_text1.pack(anchor="w")
        
        title_text2 = tk.Label(left_frame, text="FUV CHATROOM", font=(FONT, 24, "bold"), fg="DarkGoldenrod1", bg="midnight blue")
        title_text2.pack(anchor="w")
        
        # Username row
        username_text = tk.Label(right_frame, text="Username:", font=(FONT, 13), fg="white", bg="midnight blue")
        username_text.grid(row=0, column=0, sticky="e", padx=(0, 5))
        
        self.entry_username = tk.Entry(right_frame, font=(FONT, 13), width=12)
        self.entry_username.grid(row=0, column=1)
        
        
        # Arrow button (">")
        self.button = tk.Button(content_frame, text=">", font=(FONT, 9, "bold"), width=2, bg="DarkGoldenrod1", fg="midnight blue",
                                command=lambda: self.validate_username(self.entry_username.get()))
        self.button.grid(row=0, column=2, padx=(10, 0))
        
        # Set focus
        self.entry_username.focus_set()
        
        # Can enter to go next
        self.entry_username.bind("<Return>", lambda event: self.validate_username(self.entry_username.get()))

        # Exit
        self.login.protocol("WM_DELETE_WINDOW", self.graceful_exit)

    def login_screen(self):
        self.connect_to_server()
        print("Connecting to server...")
        log_event("client", "login_screen", "Attempting to connect to server...")
        
        while (not self.sio.connected):
            continue

        self.setup_login_screen()

    def setup_chatroom_screen(self):
        self.Window.deiconify()
        setup_window(self.Window, "FUV Chatroom", 900, 600)

        # Configure grid weights for resizing
        self.Window.grid_rowconfigure(1, weight=1)
        self.Window.grid_columnconfigure(0, weight=3)
        self.Window.grid_columnconfigure(1, weight=0)
        self.Window.grid_columnconfigure(2, weight=1)

        # Top layout
        self.chat_label = tk.Label(self.Window, text="FUV Chatroom", bg="midnight blue", fg="white", font=(FONT, 20, "bold"))
        self.chat_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.user_label = tk.Label(self.Window, text="You: " + self.username, font=(FONT, 14, "bold"))
        self.user_label.grid(row=3, column=2, sticky="e", padx=10)
        
        self.active_label = tk.Label(self.Window, text="Active", bg="midnight blue", fg="white", font=(FONT, 20, "bold"))
        self.active_label.grid(row=0, column=2, sticky="ew")

        # Chat box
        self.chat_box = scrolledtext.ScrolledText(
                        self.Window, 
                        width=80, 
                        height=28, 
                        state="disabled", 
                        font=(FONT, 14)  
                    )
        self.chat_box.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        # Active user list
        self.user_list = tk.Listbox(self.Window, width=28, height=28, font=(FONT, 14), 
                                    selectbackground="light blue", selectforeground="midnight blue")
        self.user_list.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        self.user_list.bind("<<ListboxSelect>>", self.on_user_selected)
        
        # Entry box (use Text widget for wrapping)
        self.entry_var = tk.StringVar()
        self.entry_box = tk.Text(
                        self.Window, 
                        width=75, 
                        height=2, 
                        font=(FONT, 14),
                        wrap="word"
                    )
        self.entry_box.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.entry_box.bind("<KeyRelease>", self.check_for_slash_command)

        # Sync entry_var with Text widget
        def sync_entry_var(event=None):
            self.entry_var.set(self.entry_box.get("1.0", "end-1c"))
            self.check_for_slash_command(event)
        self.entry_box.bind("<KeyRelease>", sync_entry_var)
        self.entry_box.bind("<FocusOut>", sync_entry_var)

        # Send button
        def send_and_clear():
            self.send_message()
            self.entry_box.delete("1.0", tk.END)
            self.entry_var.set("")
        self.send_btn = tk.Button(self.Window, text="➤", bg="DarkGoldenrod1", font=(FONT, 16), command=send_and_clear)
        self.send_btn.grid(row=2, column=1, sticky="w")

        # Bind Enter key to send message (and prevent newline)
        def send_and_prevent_newline(_):
            self.send_message()
            # Clear the entry box after sending
            self.entry_box.delete("1.0", tk.END)
            self.entry_var.set("")
            return "break"
        self.entry_box.bind("<Return>", send_and_prevent_newline)

        button_frame = tk.Frame(self.Window)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # File and Emoji Buttons - now inside the button frame
        self.file_btn = tk.Button(button_frame, text="📎", font=(FONT, 16), command=self.select_file)
        self.file_btn.pack(side="left", padx=(0, 10))  # Right padding of 10

        self.emoji_btn = tk.Button(button_frame, text="😊", font=(FONT, 16), command=self.show_emoji_picker)
        self.emoji_btn.pack(side="left")

        # Suggestion label - moved to row 4 and spans both columns
        self.suggestion_label = tk.Label(
            self.Window,
            text="Tip: Type '/w [username] [message]' to send a private message \nType '/filew [username] [filepath]' to privately send a file",
            fg="#2E86C1",
            font=(FONT, 10, "italic")
        )
        self.suggestion_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 5))
        self.suggestion_label.grid_remove()

        # Exit protocol
        self.Window.protocol("WM_DELETE_WINDOW", self.graceful_exit)
    
    def chatroom_screen(self):
        self.update_user_server()
        self.login.destroy()
        self.setup_chatroom_screen()
        self.update_user_list(self.active_users[::-1])     

    def show_emoji_picker(self):
        """Create and show the emoji picker window"""
        # if self.emoji_window and self.emoji_window.winfo_exists():
        #     self.emoji_window.lift()
        #     return
            
        # self.emoji_window = tk.Toplevel(self.Window)
        # self.emoji_window.title("Emoji Picker")
        # self.emoji_window.geometry("400x300")
        # self.emoji_window.resizable(False, False)
        if hasattr(self, 'emoji_frame') and self.emoji_frame.winfo_exists():
            self.emoji_frame.destroy()
            return

        # Create embedded frame inside chat window
        self.emoji_frame = tk.Frame(self.Window, borderwidth=1, relief="solid")
        self.emoji_frame.grid(row=5, column=0, columnspan=3, sticky="ew", padx=10, pady=5)
        
        # Create tabs for different emoji categories
        tab_control = ttk.Notebook(self.emoji_frame)
        
        # Create tabs - you can organize these as you like
        smileys_tab = ttk.Frame(tab_control)
        animals_tab = ttk.Frame(tab_control)
        foods_tab = ttk.Frame(tab_control)
        symbols_tab = ttk.Frame(tab_control)
        
        tab_control.add(smileys_tab, text="😊 Smileys")
        tab_control.add(animals_tab, text="🐻 Animals")
        tab_control.add(foods_tab, text="🍎 Foods")
        tab_control.add(symbols_tab, text="💖 Symbols")
        tab_control.pack(expand=1, fill="both")
        
        # Populate each tab with emojis
        self.populate_emoji_tab(smileys_tab, [
            "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣",
            "😊", "😇", "🙂", "🙃", "😉", "😌", "😍", "🥰",
            "😘", "😗", "😙", "😚", "😋", "😛", "😝", "😜",
            "🤪", "🤨", "🧐", "🤓", "😎", "🤩", "🥳", "😏"
        ])
        
        self.populate_emoji_tab(animals_tab, [
            "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼",
            "🐨", "🐯", "🦁", "🐮", "🐷", "🐽", "🐸", "🐵",
            "🙈", "🙉", "🙊", "🐒", "🐔", "🐧", "🐦", "🐤",
            "🐣", "🐥", "🦆", "🦅", "🦉", "🦇", "🐺", "🐗"
        ])
        
        self.populate_emoji_tab(foods_tab, [
            "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇",
            "🍓", "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝",
            "🍅", "🍆", "🥑", "🥦", "🥬", "🥒", "🌶", "🌽",
            "🥕", "🧄", "🧅", "🥔", "🍠", "🥐", "🥯", "🍞"
        ])
        
        self.populate_emoji_tab(symbols_tab, [
            "🩷", "🧡", "💛", "💚", "💙", "🩵", "💜", "🤎", "🖤", "🩶", "🤍", "💔",
            "💕", "💞", "💓", "💗", "💖", "💘", "💝", "💟", "💌", "💢", "💥", 
            "💤", "💦", "💨", "💫", "🆎", "🆘", "⛔", 
            "🛑", "📛", "❌", "⭕", "🚫", "🔇", "🔕", "🚭", "🚷", "🚯", "🚳", "🚱", 
            "🔞", "📵", "❗", "❓", "💯", "✅", "❎"
        ])
        
        # # Add search functionality
        # search_frame = tk.Frame(self.emoji_window)
        # search_frame.pack(fill="x", padx=5, pady=5)
        
        # search_var = tk.StringVar()
        # search_entry = tk.Entry(search_frame, textvariable=search_var, font=(FONT, 12))
        # search_entry.pack(side="left", fill="x", expand=True)
        
        # search_btn = tk.Button(search_frame, text="Search", command=lambda: self.search_emojis(search_var.get()))
        # search_btn.pack(side="right", padx=5)
        # Add search box inside emoji frame (at top)
        search_frame = tk.Frame(self.emoji_frame)
        search_frame.pack(fill="x", padx=5, pady=5)

        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, font=(FONT, 12))
        search_entry.pack(side="left", fill="x", expand=True)

        search_btn = tk.Button(search_frame, text="Search", command=lambda: self.search_emojis(search_var.get()))
        # hit enter to search besides clicking the button
        search_entry.bind("<Return>", lambda event: self.search_emojis(search_var.get()))
        search_btn.pack(side="right", padx=5)

    def populate_emoji_tab(self, tab, emojis):
        """Populate a tab with emoji buttons"""
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda _: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create emoji buttons in a grid
        for i, emoji in enumerate(emojis):
            btn = tk.Button(
                scrollable_frame, 
                text=emoji, 
                font=(FONT, 16), 
                command=lambda e=emoji: self.insert_emoji(e),
                width=3,
                relief="flat"
            )
            btn.grid(row=i//8, column=i%8, padx=2, pady=2)

    def search_emojis(self, query):
        """Search for emojis matching the query"""
        if not query:
            return
            
        # Create a new window for search results
        results_window = tk.Toplevel(self.emoji_window)
        results_window.title(f"Search Results for '{query}'")
        results_window.geometry("400x300")
        
        # Search in EMOJI_DICT (assuming it's {":smile:": "😊", ...})
        matches = [(code, emoji) for code, emoji in EMOJI_DICT.items() 
                  if query.lower() in code.lower()]
        
        if not matches:
            tk.Label(results_window, text="No emojis found").pack()
            return
            
        canvas = tk.Canvas(results_window)
        scrollbar = ttk.Scrollbar(results_window, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        for code, emoji in matches:
            frame = tk.Frame(scrollable_frame)
            frame.pack(fill="x", padx=5, pady=2)
            
            tk.Label(frame, text=emoji, font=(FONT, 16)).pack(side="left")
            tk.Label(frame, text=code, font=(FONT, 12)).pack(side="left", padx=10)
            
            btn = tk.Button(
                frame, 
                text="Insert", 
                command=lambda e=emoji: self.insert_emoji(e),
                width=6
            )
            btn.pack(side="right")

    def insert_emoji(self, emoji):
        """Insert the selected emoji into the message input at the current cursor position (Unicode-safe)"""
        try:
            # Insert emoji at the current cursor position in the Text widget
            self.entry_box.insert(tk.INSERT, emoji)
            # Update entry_var to reflect the new text
            self.entry_var.set(self.entry_box.get("1.0", "end-1c"))
            # Move cursor after the inserted emoji
            self.entry_box.mark_set(tk.INSERT, self.entry_box.index(tk.INSERT))
            self.entry_box.focus_set()

            # Close the emoji picker if open
            if hasattr(self, 'emoji_window') and self.emoji_window and self.emoji_window.winfo_exists():
                self.emoji_window.destroy()
                self.emoji_window = None

        except Exception as e:
            print(f"Error inserting emoji: {e}")
            log_event("client", "insert_emoji_error", f"Error inserting emoji: {e}")

    def select_file(self, path = None, recipient = "Global"):
        if recipient == "Global":
            filepath = filedialog.askopenfilename()
        else:
            filepath = path
        
        accept_extension = ["mp4", "jpeg", "jpg", "mp3", "png"]
        
        if filepath:
            try: 
                f_size_bytes = os.path.getsize(filepath)
                f_size_mb = f_size_bytes / (1000*1000)
                
                extension = os.path.splitext(filepath)[1]
                extension = extension[1:].lower()

                if extension in accept_extension:
                    if f_size_mb <= 25:
                        # self.display_system_message(f"Selected file: {filepath.split('/')[-1]}")
                        if recipient == "Global":
                            threading.Thread(target=self.send_file_w_progressbar, args=(filepath,), daemon=True).start()
                        else:
                            threading.Thread(target=self.send_file_w_progressbar, args=(filepath, recipient,), daemon=True).start()
                    else:
                        messagebox.showwarning("Warning", "Please choose a file smaller than 20 MB.")
                else:
                    messagebox.showwarning("Warning", "Inappropriate file type (not video, image, or audio)")
                    log_event("client", "select_file_error", f"Incorrect file type error: {extension}")
            
            except Exception as e:
                messagebox.showerror("Error", "Inappropriate file path")    
            
    def send_file_w_progressbar(self, path, recipient = "Global"):      
        try:
            filename = os.path.basename(path)
            f_size_b = os.path.getsize(path)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            chunk_num = 0
            total_chunks = math.ceil(f_size_b/CHUNK_SIZE)
            
            # Hashing file
            hash_algo = hashlib.sha256()
            
            # self.display_system_message(f"[Upload file] Waiting for server confirmation...")
            if recipient == "Global":
                self.display_progress_bar("Global", self.username, timestamp, filename)
            else:
                self.display_progress_bar("Private", f"To {recipient}", timestamp, filename)
            
            self.sio.emit('start_upload', {
                          'filename': filename,
                          'sender': self.username, 
                          'recipient': recipient
                         })
            
            with open(path, "rb") as file:
                while True:
                    chunk = file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    hash_algo.update(chunk)

                    encoded_data = base64.b64encode(chunk).decode()
                    self.sio.emit('upload_chunk', {
                                  'filename': filename,
                                  'recipient': recipient,
                                  'chunk_data': encoded_data
                                 })
                    chunk_num += 1
                    self.update_progress(filename, chunk_num, total_chunks)
                    # print(f"[DEBUG] Writing {threading.current_thread().name}, {filename}")
                    time.sleep(0.05)
                    
            time.sleep(0.5)
            self.sio.emit('finish_upload', {
                          'filename': filename, 
                          'sender': self.username,
                          'recipient': recipient,
                          'hash_file': hash_algo.hexdigest(),
                          'time': timestamp})
            print(hash_algo.hexdigest())
            
        except Exception as e:
            messagebox.showerror("Error", f"File transfer failed {e}")
    
    def error_upload(self, filename):
        try:
            bar_info = self.progress_n_index.get(filename)
            
            if not bar_info:
                return
            
            self.chat_box.config(state="normal")    
            progressbar_pos = bar_info["index"]
            
            try:
                bar_info["bar"].destroy() # Remove the progress bar
                self.chat_box.delete(progressbar_pos) # Delete window element
                
                # Insert error text at the same index
                self.chat_box.insert(progressbar_pos, "❌ Error\n")
            except Exception as e:
                print(f"Error {e}")
                log_event("client", "progress_bar_error", f"Error destroying progress bar for {filename}: {e}")
            
            self.chat_box.config(state="disabled")
            self.chat_box.yview(tk.END)
            
            self.progress_n_index.pop(filename, None)
            
        except Exception as e:
            print("Cannot display the upload error.")
            log_event("client", "error_upload_error", f"Cannot display the upload error for {filename}: {e}") 
    
    def update_progress(self, filename, chunk_num, total_chunks):
        try:
            bar_info = self.progress_n_index.get(filename)
            
            if not bar_info:
                return
            
            percent = math.floor((chunk_num/total_chunks) * 100)

            if percent == 100:
                self.chat_box.config(state="normal")
                
                progressbar_pos = bar_info["index"]
                
                def finalize_upload():
                    # Check if retry was already triggered
                    if filename not in self.upload_confirmation:
                        return  # already handled

                    try:
                        bar_info["bar"].destroy() # Remove the progress bar
                        self.chat_box.delete(progressbar_pos) # Delete window element
                    except Exception as e:
                        print(f"Error {e}")
                        log_event("client", "progress_bar_error", f"Error destroying progress bar for {filename}: {e}")
                    
                    # Insert the download button
                    download_button = tk.Button(self.chat_box, text = "⬇", command = lambda : self.ask_download(filename), 
                                        bg="midnight blue", fg="white", relief="flat", width= 2, 
                                        padx=0, pady=0, font=(FONT, 11))
                    self.chat_box.window_create(progressbar_pos, window = download_button, pady=3)
                    
                    self.chat_box.config(state="disabled")
                    self.chat_box.yview(tk.END)
                    
                    self.progress_n_index.pop(filename, None)
                    self.upload_confirmation.pop(filename, None)
                
                # Only check the first time progress reaches 100% -> only schedule once
                if filename not in self.upload_confirmation:
                    self.upload_confirmation[filename] = self.root.after(2000, finalize_upload) # Delay 2s to wait for 'retry_sending' signal from server
            else:
                bar_info["bar"]["value"] = percent
            
        except Exception as e:
            print(f"Cannot upload the progress bar of {filename}")
            log_event("client", "progress_bar_update_error", f"Cannot update progress bar for {filename}: {e}")
    
    def display_progress_bar(self, msg_type, sender, timestamp, filename):
        self.chat_box.config(state="normal")
        tag = "blue" if msg_type == "Global" else "orange"
        formatted = f"({msg_type}) ({sender}) ({timestamp}): {filename} "
        self.chat_box.insert(tk.END, formatted, tag)
        
        # Add progress bar at the end of the file uploading announcement
        bar = Progressbar(self.chat_box, orient = tk.HORIZONTAL, mode="determinate", maximum=100, length=50)
        self.chat_box.window_create(tk.END, window=bar, pady=3)  

        progressbar_pos = self.chat_box.index(bar)      
        self.chat_box.insert(tk.END, "\n")
        
        self.chat_box.tag_config("blue", foreground="midnight blue")
        self.chat_box.tag_config("orange", foreground="darkorange")
        
        # Store the position of the progress bar for later replacing with the download button
        self.progress_n_index[filename] = {"index": progressbar_pos, 'bar': bar}
        
        self.chat_box.config(state="disabled")
        self.chat_box.yview(tk.END)
    
    def save_file_stream(self, filename):
        file_path = self.download_files[filename]['path']
        queue = self.download_files[filename]['queue']
        computed_hash = self.download_files[filename]['computed_hash']
        
        try:
            with open(file_path, "wb") as f:
                while True:
                    chunk = queue.get()
                    if chunk is None:  # Poison pill
                        break
                    
                    decoded_chunk = base64.b64decode(chunk.encode())
                    
                    f.write(decoded_chunk)
                    computed_hash.update(decoded_chunk)
        except Exception as e:
            messagebox.showerror("Error", "Failed to write chunk when downloading.")
            log_event("client", "save_file_stream_failed", f"Failed to write chunk when downloading {filename}: {e}")
        finally:
            self.download_files.pop(filename)
    
    def ask_download(self, filename):
        if messagebox.askyesno("Download", f"Do you want to download {filename}?"):
            extension = os.path.splitext(filename)[1]  # get original file extension
            save_path = filedialog.asksaveasfilename(title="Save As", initialfile=filename)
            
            if save_path:
                if not save_path.lower().endswith(extension.lower()):
                    save_path += extension  # auto-append if user forgot
                    
                q = Queue()
                hash_algo_download = hashlib.sha256()
                
                self.download_files[filename] = {
                    'queue': q,
                    'path': save_path,
                    'thread': threading.Thread(target=self.save_file_stream, args=(filename,), daemon=True),
                    'computed_hash': hash_algo_download
                }

                self.download_files[filename]['thread'].start()
                
                self.sio.emit('download_request', {'filename': filename})
    
    def receive_file(self, msg_type, sender, filename, timestamp):
        self.chat_box.config(state="normal")
        tag = "blue" if msg_type == "Global" else "orange"
        formatted = f"({msg_type}) ({sender}) ({timestamp}): {filename} "
        self.chat_box.insert(tk.END, formatted, tag)
        
        download_button = tk.Button(self.chat_box, text = "⬇", command = lambda : self.ask_download(filename), 
                                    bg="midnight blue", fg="white", relief="flat", width= 2, 
                                    padx=0, pady=0, font=(FONT, 11))
        self.chat_box.window_create(tk.END, window = download_button, pady=3)
        self.chat_box.insert(tk.END, "\n")
        
        self.chat_box.tag_config("blue", foreground="midnight blue")
        self.chat_box.tag_config("orange", foreground="darkorange")
        self.chat_box.config(state="disabled")
        self.chat_box.yview(tk.END)
    
    def check_for_slash_command(self, event):
        """Check if user typed '/' and show suggestion"""
        current_text = self.entry_var.get()
        
        # Show suggestion if user types '/' at start of message
        if current_text.startswith('/'):
            self.suggestion_label.grid()
        elif not current_text.startswith('/'):
            self.suggestion_label.grid_remove()
    
    def send_message(self):
        raw_msg = self.entry_var.get()
        if raw_msg.strip() == "":
            return

        # Replace emoji codes with actual emojis
        for code, emoji in EMOJI_DICT.items():
            raw_msg = raw_msg.replace(code, emoji)

        timestamp = datetime.now().strftime("%H:%M:%S")

        if raw_msg.startswith("/filew "):
            parts = raw_msg.split(maxsplit=2)
            
            if len(parts) >= 3:
                recipient = parts[1]
                file_path = parts[2]
                self.select_file(file_path, recipient)
        
        elif raw_msg.startswith("/w "):
            parts = raw_msg.split(maxsplit=2)
            if len(parts) >= 3:
                recipient = parts[1]
                message_content = parts[2]  
                plaintext = f"{timestamp}|{message_content}" 
                # encrypted_msg = encrypt_message(plaintext)
                # --- CHECK IF RECIPIENT IS IN ACTIVE USERS ---
                if recipient not in self.active_users:
                    messagebox.showwarning("Warning", f"User '{recipient}' does not exist or is not active.")
                    return
                encrypted_msg = encrypt_aes(self.session_aes_key, plaintext)

                self.sio.emit('private_message', {
                    'recipient': recipient,
                    'message': encrypted_msg,
                    'sender': self.username
                })

                self.display_message("Private", f"To {recipient}", message_content, timestamp)

            else:
                self.display_system_message("Invalid private message format. Use '/w username message'")
                return
        else:
            message_content = raw_msg
            plaintext = f"{timestamp}|{message_content}"  
            encrypted_msg = encrypt_aes(self.session_aes_key, plaintext)


            self.sio.emit('global_message', {
                'message': encrypted_msg,
                'sender': self.username
            })

        self.entry_var.set("")

    def display_message(self, msg_type, sender, message, timestamp):
        self.chat_box.config(state="normal")
        tag = "blue" if msg_type == "Global" else "orange"
        # Insert colored metadata
        metadata = f"({msg_type}) ({sender}) ({timestamp}): "
        self.chat_box.insert(tk.END, metadata, tag)
        # Insert message content in default color (black)
        self.chat_box.insert(tk.END, f"{message}\n")
        self.chat_box.tag_config("blue", foreground="#0229A7")
        self.chat_box.tag_config("orange", foreground="darkorange")
        self.chat_box.config(state="disabled")
        self.chat_box.yview(tk.END)

    def display_system_message(self, message):
        if not hasattr(self, 'chat_box'):
            print("Chat box not initialized.")
            log_event("client", "display_system_message_error", "Chat box not initialized.")
            return
        
        self.chat_box.config(state="normal")
        
        formatted = f"(System) ({datetime.now().strftime('%H:%M:%S')}): {message} \n"
        self.chat_box.insert(tk.END, formatted, "gray")
        self.chat_box.tag_config("gray", foreground="gray")
        self.chat_box.config(state="disabled")
        self.chat_box.yview(tk.END)

    def private_sending_box(self, recipient):
        self.private_box = tk.Toplevel()
        setup_window(self.private_box, "Direct message", 300, 100)
        self.private_box.resizable(False, False)
        
        # Blocking the main window, only interacting with the dialog
        self.private_box.grab_set()
        
        # Configure the grid for padding and centering
        self.private_box.columnconfigure(0, weight=1)
        
        # Add label
        self.question = tk.Label(self.private_box, text=f"Sending to {recipient}", font=(FONT, 14, "bold"))
        self.question.grid(row=0, column=0, pady = (15, 0))

        # Button commands
        def pfile():
            file_path = filedialog.askopenfilename()
            
            if file_path:
                self.select_file(file_path, recipient)
                self.clear_n_exit()
        
        def pmessage():
            # Call pmessage method from the class
            self.pmessage(recipient)

        def clear_n_exit():
            self.private_box.destroy()
            self.user_list.selection_clear(0, tk.END)
            self.user_list.activate(-1)                    # Remove active item
            self.user_list.selection_anchor(0)             # Reset anchor
        
        self.button_frame = tk.Frame(self.private_box)
        self.button_frame.grid(row=1, column=0, pady=(5, 10))
        
        self.private_file = tk.Button(self.button_frame, text="File", font=(FONT, 10), width=10, 
                                      bg= "light blue", fg="midnight blue", command=pfile)
        self.private_file.grid(row=0, column=0, padx=5)
        
        self.private_message = tk.Button(self.button_frame, text="Message", font=(FONT, 10), width=10, 
                                         bg= "light blue", fg="midnight blue", command=pmessage)
        self.private_message.grid(row=0, column=1, padx=5)
        
        # Exit
        self.private_box.protocol("WM_DELETE_WINDOW", clear_n_exit)

    def pmessage(self, recipient):
        # Clear any existing private message box
        self.private_box.destroy()
        self.user_list.selection_clear(0, tk.END)
        self.user_list.activate(-1)  # Remove active item
        self.user_list.selection_anchor(0)  # Reset anchor

        # Set the text for the message box
        text = f"/w {recipient} "
        self.entry_var.set(text)  # Update the entry_var to reflect the new text in the entry box
        self.entry_box.delete(1.0, tk.END)  # Clear the current text in the entry box
        self.entry_box.insert(tk.END, text)  # Insert the text into the entry box
        self.check_for_slash_command(None)  # Handle slash command suggestions

        # Set the cursor position after the inserted text
        self.entry_box.mark_set(tk.INSERT, tk.END)  # Place the cursor at the end of the text

        # Focus the entry box to allow further typing
        self.entry_box.focus()  
    
    # Event handler for user selection in the user list
    def on_user_selected(self, event):
        selected_indices = self.user_list.curselection()
        if selected_indices:
            index = selected_indices[0]
            value = self.user_list.get(index)
            username = value[2:].strip()
            print(f"User clicked: {username}")
            log_event("client", "user_selected", f"User selected: {username}")
            
            self.private_sending_box(username)

    def update_user_list(self, users):
        if (not hasattr(self, 'user_list') or 
            self.user_list is None or 
            not isinstance(users, list)
        ):
            print("User list not initialized or invalid users data.")
            log_event("client", "update_user_list_error", "User list not initialized or invalid users data.")
            return
        
        # Clear the current list
        self.user_list.delete(0, tk.END)
        for user in users:
            self.user_list.insert(tk.END, f"👤 {user}")

    def graceful_exit(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            try:
                if self.sio.connected:
                    self.sio.disconnect()   
            except:
                pass
            self.Window.destroy()
    
    def force_exit(self):
        """Force exit the application without confirmation."""
        try:
            if self.sio.connected:
                self.sio.disconnect()
        except:
            pass
        self.Window.destroy()
        
if __name__ == "__main__":
    app = ChatClientGUI()