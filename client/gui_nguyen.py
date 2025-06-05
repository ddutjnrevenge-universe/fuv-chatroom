import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from datetime import datetime
import socket
import threading
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.constants import HOST, PORT, BUFFER_SIZE
from emoji_dict import EMOJI_DICT

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y - 10}')

def setup_window(window, title, width, height):
    window.title(title)
    window.resizable(False, False)
    window.configure(width=width, height=height)
    center_window(window, width, height)

class ChatClientGUI:
    def __init__(self):
        # self.root = root
        # self.username = None
        # self.client_socket = None
        # self.emoji_window = None

        # self.prompt_username()
        # self.setup_gui()
        self.root = tk.Tk()
        self.root.withdraw()  # Hide main window until login
        self.emoji_window = None
        self.username = None
        self.client_socket = None
        self.send_file = False
        self.login_screen()
        self.root.mainloop()

    def login_screen(self):
        self.login = tk.Toplevel()
        setup_window(self.login, "FUV Chatroom Login", 600, 400)

        tk.Label(self.login, text="Login", font=("Arial", 20, "bold")).place(relx=0.5, rely=0.2, anchor="center")

        tk.Label(self.login, text="Username:", font=("Arial", 14, "bold")).place(relx=0.15, rely=0.3)

        self.entry_username = tk.Entry(self.login, font=("Arial", 14))
        self.entry_username.place(relwidth=0.45, relheight=0.08, relx=0.35, rely=0.294)

        self.entry_username.bind("<Return>", lambda event: self.goto_chatroom(self.entry_username.get()))
        tk.Button(self.login, text="→", font=("Arial", 14), command=lambda: self.goto_chatroom(self.entry_username.get())).place(relx=0.5, rely=0.5, anchor="center")

        self.login.protocol("WM_DELETE_WINDOW", self.graceful_exit)

    def goto_chatroom(self, username):
        if username.strip() == "":
            messagebox.showwarning("Warning", "Please input a username")
            return
        elif len(username.strip()) > 12:
            messagebox.showwarning("Warning", "Username too long")
            return

        self.username = username.strip()
        self.login.destroy()
        self.setup_gui()
        self.root.deiconify()
        self.root.title(f"FUV Chatroom - {self.username}")
        self.connect_to_server()

    def connect_to_server(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
            self.client_socket.send(self.username.encode())
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not connect to server: {e}")

    def setup_gui(self):
        self.root.title("FUV Chatroom")
        self.root.minsize(900, 600)

        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(2, weight=1)

        self.chat_label = tk.Label(self.root, text="FUV Chatroom", bg="midnight blue", fg="white", font=("Arial", 20, "bold"))
        self.chat_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.user_label = tk.Label(self.root, text="Active", bg="midnight blue", fg="white", font=("Arial", 16))
        self.user_label.grid(row=0, column=2, sticky="ew")

        self.chat_box = scrolledtext.ScrolledText(self.root, width=80, height=28, state="disabled", font=("Arial", 14))
        self.chat_box.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        self.user_list = tk.Listbox(self.root, width=28, height=28, font=("Arial", 14))
        self.user_list.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")

        button_frame = tk.Frame(self.root)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        self.file_btn = tk.Button(button_frame, text="📎", font=("Arial", 16), command=self.select_file)
        self.file_btn.pack(side="left", padx=(0, 10))  # Right padding of 10

        self.emoji_btn = tk.Button(button_frame, text="😊", font=("Arial", 16), command=self.show_emoji_picker)
        self.emoji_btn.pack(side="left")

        # Suggestion label below the two buttons
        self.suggestion_label = tk.Label(self.root, text="Tip: Use '/w [username] [message]' for private message", fg="gray", font=("Arial", 10, "italic"))
        self.suggestion_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 5))
        self.suggestion_label.grid_remove()

        self.entry_var = tk.StringVar()
        self.entry_box = tk.Entry(self.root, textvariable=self.entry_var, font=("Arial", 14))
        self.entry_box.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        self.entry_box.bind("<Return>", lambda event: self.send_message())
        self.entry_box.bind("<KeyRelease>", self.check_for_slash_command)

        self.send_btn = tk.Button(self.root, text="➤", bg="DarkGoldenrod1", font=("Arial", 16), command=self.send_message)
        self.send_btn.grid(row=2, column=1, sticky="w")

        self.root.protocol("WM_DELETE_WINDOW", self.graceful_exit)
    def show_emoji_picker(self):
        """Create and show the emoji picker window"""
        if self.emoji_window and self.emoji_window.winfo_exists():
            self.emoji_window.lift()
            return
            
        self.emoji_window = tk.Toplevel(self.root)
        self.emoji_window.title("Emoji Picker")
        self.emoji_window.geometry("400x300")
        self.emoji_window.resizable(False, False)
        
        # Create tabs for different emoji categories
        tab_control = ttk.Notebook(self.emoji_window)
        
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
            "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍",
            "🤎", "💔", "❣️", "💕", "💞", "💓", "💗", "💖",
            "💘", "💝", "💟", "☮️", "✝️", "☪️", "🕉", "☸️",
            "✡️", "🔯", "🕎", "☯️", "☦️", "🛐", "⛎", "♈️"
        ])
        
        # Add search functionality
        search_frame = tk.Frame(self.emoji_window)
        search_frame.pack(fill="x", padx=5, pady=5)
        
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Arial", 12))
        search_entry.pack(side="left", fill="x", expand=True)
        
        search_btn = tk.Button(search_frame, text="Search", command=lambda: self.search_emojis(search_var.get()))
        search_btn.pack(side="right", padx=5)

    def populate_emoji_tab(self, tab, emojis):
        """Populate a tab with emoji buttons"""
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
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
        
        # Create emoji buttons in a grid
        for i, emoji in enumerate(emojis):
            btn = tk.Button(
                scrollable_frame, 
                text=emoji, 
                font=("Arial", 16), 
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
        
        for i, (code, emoji) in enumerate(matches):
            frame = tk.Frame(scrollable_frame)
            frame.pack(fill="x", padx=5, pady=2)
            
            tk.Label(frame, text=emoji, font=("Arial", 16)).pack(side="left")
            tk.Label(frame, text=code, font=("Arial", 12)).pack(side="left", padx=10)
            
            btn = tk.Button(
                frame, 
                text="Insert", 
                command=lambda e=emoji: self.insert_emoji(e),
                width=6
            )
            btn.pack(side="right")

    def insert_emoji(self, emoji):
        # """Insert the selected emoji into the message input"""
        # current_text = self.entry_var.get()
        # self.entry_var.set(current_text + emoji)
        # self.entry_box.focus()
        
        # # Close the emoji picker if open
        # if self.emoji_window and self.emoji_window.winfo_exists():
        #     self.emoji_window.destroy()
        #     self.emoji_window = None
        """Insert the selected emoji into the message input with correct cursor position"""
        try:
            current_pos = self.entry_box.index(tk.INSERT)
            current_text = self.entry_var.get()
            
            # Insert emoji at current cursor position
            new_text = current_text[:current_pos] + emoji + current_text[current_pos:]
            self.entry_var.set(new_text)
            
            # Move cursor to position after the emoji
            # Note: Some emojis are 2 characters long in Python's string representation
            cursor_increment = len(emoji.encode('utf-16-le')) // 2
            self.entry_box.icursor(current_pos + cursor_increment)
            self.entry_box.focus()
            
            # Close the emoji picker if open
            if self.emoji_window and self.emoji_window.winfo_exists():
                self.entry_box.focus_set()
                self.emoji_window.destroy()
                self.emoji_window = None
                
        except Exception as e:
            print(f"Error inserting emoji: {e}")

    def select_file(self):
        filepath = filedialog.askopenfilename()
        
        accept_extension = ["mp4", "jpeg", "jpg", "mp3", "png"]
        
        if filepath:
            f_size_bytes = os.path.getsize(filepath)
            f_size_mb = f_size_bytes / (1024*1024)
            
            extension = os.path.splitext(filepath)[1]
            extension = extension[1:].lower()

            if extension in accept_extension:
                if f_size_mb <= 25:
                    self.send_file = True
                    self.display_system_message(f"Selected file: {filepath.split('/')[-1]}")
                    # You would later send this file to the server
                else:
                    messagebox.showwarning("Warning", "Please choose a file smaller than 25 MB.")
            else:
                messagebox.showwarning("Warning", "Inappropriate file type (not video, image, or audio)")
                
    def receive_messages(self):
        while True:
            try:
                msg = self.client_socket.recv(BUFFER_SIZE).decode()
                if msg == "__USERNAME_TAKEN__":
                    messagebox.showerror("Username Error", "This username is already taken. Please try another username.")
                    self.client_socket.close()
                    self.root.withdraw()
                    self.login_screen()
                    break
                elif msg.startswith("__USER_LIST__:"):
                    users = json.loads(msg.split(":", 1)[1])
                    self.update_user_list(users)
                elif msg.startswith("(Private)"):
                    # Extract sender from the message using format: (Private) (sender): content
                    parts = msg.split(")", 2)
                    sender_info = parts[1].strip(" ()")
                    content = parts[2].strip()
                    sender = "You" if sender_info.startswith(self.username) else sender_info
                    self.display_message("Private", sender, f"{sender_info}: {content}")

                elif msg.startswith("(Global)"):
                    # Extract sender from the message using format: (Global) (sender): content
                    parts = msg.split(")", 2)
                    sender_info = parts[1].strip(" ()")
                    content = parts[2].strip()
                    if sender_info == self.username:
                        sender = "You"
                    else:
                        sender = sender_info
                    self.display_message("Global", sender, f"{sender_info}: {content}")
                else:
                    self.display_system_message(msg)
            except Exception as e:
                print(f"[ERROR] {e}")
                break

    def send_message(self):
        raw_msg = self.entry_var.get()
        if raw_msg.strip() == "":
            return

        for code, emoji in EMOJI_DICT.items():
            raw_msg = raw_msg.replace(code, emoji)

        try:
            self.client_socket.send(raw_msg.encode())
        except Exception as e:
            self.display_system_message(f"Failed to send message: {e}")

        self.entry_var.set("")

    def display_message(self, msg_type, sender, message):
        self.chat_box.config(state="normal")
        tag = "blue" if msg_type == "Global" else "orange"
        timestamp = datetime.now().strftime("%H:%M:%S")

        display_sender = "You" if sender == "You" else sender
        formatted = f"({msg_type}) ({display_sender}) ({timestamp}){message.split(':', 1)[1]}\n"
        self.chat_box.insert(tk.END, formatted, tag)
        self.chat_box.tag_config("blue", foreground="blue")
        self.chat_box.tag_config("orange", foreground="darkorange")
        self.chat_box.config(state="disabled")
        self.chat_box.yview(tk.END)

    def display_system_message(self, message):
        self.chat_box.config(state="normal")

        if self.send_file == True:
            status = "(Sent)"
        else:
            status = ""
        
        print(status)

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted = f"(System) ({timestamp}): {message}\n"
        self.chat_box.insert(tk.END, formatted, "gray")
        self.chat_box.tag_config("gray", foreground="gray")
        self.chat_box.config(state="disabled")
        self.chat_box.yview(tk.END)

    def update_user_list(self, user_list):
        self.user_list.delete(0, tk.END)
        for user in user_list:
            prefix = "●"
            self.user_list.insert(tk.END, f"{prefix} {user}")

    def check_for_slash_command(self, event):
        if self.entry_var.get().startswith("/"):
            self.suggestion_label.grid()
        else:
            self.suggestion_label.grid_remove()

    def graceful_exit(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            try:
                self.client_socket.close()
            except:
                pass
            self.root.destroy()

if __name__ == "__main__":
    # root = tk.Tk()
    # app = ChatClientGUI(root)
    # root.mainloop()
    ChatClientGUI()
    