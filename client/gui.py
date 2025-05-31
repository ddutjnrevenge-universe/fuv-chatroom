# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from datetime import datetime
from emoji_dict import EMOJI_DICT

FONT = "Helvetica"

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y - 10}')

def setup_window(window, title, width, height):
    window.title(title)
    window.resizable(False, False)
    window.configure(width = width, height = height)
    center_window(window, width, height)

class ChatClientGUI:
    def __init__(self):
        self.Window = tk.Tk()
        self.Window.withdraw()

        self.emoji_window = None
        self.username = None
        self.send_file = False
        self.active_users = ["th","FUV-User-1", "FUV-User-2", "FUV-User-3"]
        
        self.login_screen()
        self.Window.mainloop()

    def login_screen(self):
        self.login = tk.Toplevel()
        setup_window(self.login, "FUV Chatroom Login", 600, 400)
        
        # Use Grid Layout later if typing the password
        self.text = tk.Label(self.login, text = "Login", font = (FONT, 20, "bold"))
        self.text.place(relx=0.5, rely=0.2, anchor="center")
        
        self.username = tk.Label(self.login, text = "Username:", font = (FONT, 14, "bold"))
        self.username.place(relx=0.15, rely=0.3)
        
        self.entry_username = tk.Entry(self.login, font = (FONT, 14))
        self.entry_username.place(relwidth=0.45, relheight=0.08, relx=0.35, rely=0.294)
        
        # Can push button to go next
        self.button = tk.Button(self.login, text = "→", font=(FONT, 14),
                                command = lambda : self.goto_chatroom(self.entry_username.get()))
        self.button.place(relx=0.5, rely=0.5, anchor="center")
        
        # Can enter to go next
        self.entry_username.bind("<Return>", lambda event: self.goto_chatroom(self.entry_username.get()))
        
        # Exit
        self.login.protocol("WM_DELETE_WINDOW", self.graceful_exit)
    
    def goto_chatroom(self, username):
        if username.strip() == "":
            # Dont allow an empty username
            messagebox.showwarning("Warning", "Please input an username")
            return
        elif len(username.strip()) > 9:
            # Dont allow long usernames
            messagebox.showwarning("Warning", "Please input a shorter username")
            return
        elif username in self.active_users:
            # Dont allow duplicate username
            messagebox.showwarning("Warning", "This username has already been used. Please choose another username.")
            return
        
        self.login.destroy()
        self.chatroom_screen(username)
        
        self.update_user_list(self.active_users[::-1])
        self.active_users.append(username)
            
    def chatroom_screen(self, username):
        self.Window.deiconify()
        setup_window(self.Window, "FUV Chatroom", 900, 600)
        
        self.username = username
        
        # Configure grid weights for resizing
        self.Window.grid_rowconfigure(1, weight=1)
        self.Window.grid_columnconfigure(0, weight=3)
        self.Window.grid_columnconfigure(1, weight=0)
        self.Window.grid_columnconfigure(2, weight=1)

        # Top layout
        self.chat_label = tk.Label(self.Window, text="FUV Chatroom", bg="midnight blue", fg="white", font=("Arial", 20, "bold"))
        self.chat_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.user_label = tk.Label(self.Window, text="You: " + username, font=("Arial", 10))
        self.user_label.grid(row=3, column=2, sticky="e", padx=10)
        
        self.active_label = tk.Label(self.Window, text="Active", bg="midnight blue", fg="white", font=("Arial", 16))
        self.active_label.grid(row=0, column=2, sticky="ew")

        # Chat box
        # self.chat_box = scrolledtext.ScrolledText(self.Window, width=80, height=28, state="disabled", font=("Arial", 14))
        self.chat_box = scrolledtext.ScrolledText(
                        self.Window, 
                        width=80, 
                        height=28, 
                        state="disabled", 
                        font=("Arial", 14)  
                    )
        self.chat_box.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        # Active user list
        self.user_list = tk.Listbox(self.Window, width=28, height=28, font=("Arial", 14))
        self.user_list.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")

        # Entry box
        self.entry_var = tk.StringVar()
        # self.entry_box = tk.Entry(self.Window, textvariable=self.entry_var, width=75, font=("Arial", 14))
        self.entry_box = tk.Entry(
                        self.Window, 
                        textvariable=self.entry_var, 
                        width=75, 
                        font=("Arial", 14)  
                    )
        self.entry_box.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        # Add this binding after creating the entry box
        self.entry_box.bind("<KeyRelease>", self.check_for_slash_command)

        # Send button
        self.send_btn = tk.Button(self.Window, text="➤", bg="DarkGoldenrod1", font=("Arial", 16), command=self.send_message)
        self.send_btn.grid(row=2, column=1, sticky="w")

        # Bind Enter key to send message
        self.entry_box.bind("<Return>", lambda event: self.send_message())

        # # File and Emoji Buttons
        # self.file_btn = tk.Button(self.Window, text="📎", font=("Arial", 16), command=self.select_file)
        # self.file_btn.grid(row=3, column=0, sticky="w", padx=10)

        # self.emoji_btn = tk.Button(self.Window, text="😊", font=("Arial", 16), command=self.insert_emoji)
        # self.emoji_btn.grid(row=3, column=0, sticky="w", padx=60)
        # Bottom button layout - create a frame to contain the buttons
        button_frame = tk.Frame(self.Window)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=5)

        # # File and Emoji Buttons
        # self.file_btn = tk.Button(self.Window, text="📎", font=("Arial", 16), command=self.select_file)
        # self.file_btn.grid(row=3, column=0, sticky="w", padx=10)

        # # Change emoji button to open picker
        # self.emoji_btn = tk.Button(self.Window, text="😊", font=("Arial", 16), command=self.show_emoji_picker)
        # self.emoji_btn.grid(row=3, column=0, sticky="w", padx=60)

        # File and Emoji Buttons - now inside the button frame
        self.file_btn = tk.Button(button_frame, text="📎", font=("Arial", 16), command=self.select_file)
        self.file_btn.pack(side="left", padx=(0, 10))  # Right padding of 10

        self.emoji_btn = tk.Button(button_frame, text="😊", font=("Arial", 16), command=self.show_emoji_picker)
        self.emoji_btn.pack(side="left")

        # Suggestion label - moved to row 4 and spans both columns
        self.suggestion_label = tk.Label(
            self.Window,
            text="Tip: Type '/p [username] [message]' to send a private message",
            fg="#2E86C1",
            font=("Arial", 10, "italic")
        )
        self.suggestion_label.grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 5))
        self.suggestion_label.grid_remove()
        
        # Exit protocol
        self.Window.protocol("WM_DELETE_WINDOW", self.graceful_exit)

    def show_emoji_picker(self):
        """Create and show the emoji picker window"""
        if self.emoji_window and self.emoji_window.winfo_exists():
            self.emoji_window.lift()
            return
            
        self.emoji_window = tk.Toplevel(self.Window)
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

    def check_for_slash_command(self, event):
        """Check if user typed '/' and show suggestion"""
        current_text = self.entry_var.get()
        
        # Show suggestion if user types '/' at start of message
        if current_text.startswith('/') and len(current_text) == 1:
            self.suggestion_label.grid()
        elif not current_text.startswith('/'):
            self.suggestion_label.grid_remove()
        
    def send_message(self):
        raw_msg = self.entry_var.get()
        if raw_msg.strip() == "":
            return

        # Replace emoji text with Unicode
        for code, emoji in EMOJI_DICT.items():
            raw_msg = raw_msg.replace(code, emoji)

        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Handle private messages (/w username message)
        if raw_msg.startswith("/p "):
            msg_type = "Private"
            # Split the message into parts
            parts = raw_msg.split(maxsplit=2)  # Split into ["/w", "username", "message"]
            if len(parts) >= 3:
                recipient = parts[1]
                message_content = parts[2]
                # Format the displayed message without the /w command
                formatted_msg = f"(To: {recipient}) {message_content}"
            else:
                # Show error for invalid format
                self.display_system_message("Invalid private message format. Use '/w username message'")
                return
        else:
            msg_type = "Global"
            formatted_msg = raw_msg

        self.display_message(msg_type, self.username, formatted_msg, timestamp)
        self.entry_var.set("")

    def display_message(self, msg_type, sender, message, timestamp):
        self.chat_box.config(state="normal")
        tag = "blue" if msg_type == "Global" else "orange"
        formatted = f"({msg_type}) ({sender}) ({timestamp}): {message}\n"
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
        
        formatted = f"(System) ({datetime.now().strftime('%H:%M:%S')}): {message} {status}\n"
        self.chat_box.insert(tk.END, formatted, "gray")
        self.chat_box.tag_config("gray", foreground="gray")
        self.chat_box.config(state="disabled")
        self.chat_box.yview(tk.END)

    def update_user_list(self, users):
        self.user_list.delete(0, tk.END)
        for user in users:
            self.user_list.insert(tk.END, f"● {user}")
        
    def graceful_exit(self):
        # TODO: send disconnect message to server
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.Window.destroy()

if __name__ == "__main__":
    app = ChatClientGUI()