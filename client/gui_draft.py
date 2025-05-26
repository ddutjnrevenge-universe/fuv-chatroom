import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from datetime import datetime
from emoji_dict import EMOJI_DICT

BG_COLOR = 0
TXT_COLOR = 0
W_WIDTH = 600
W_HEIGHT = 400
FONT = "Helvetica"

def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    window.geometry(f'{width}x{height}+{x}+{y - 10}')

def setup_window(window, title):
    window.title(title)
    window.resizable(False, False)
    window.configure(width=W_WIDTH, height=W_HEIGHT)
    center_window(window, W_WIDTH, W_HEIGHT)

class ClientGUI:
    def __init__ (self, ):
        self.Window = tk.Tk()
        self.Window.withdraw()
        
        self.login_screen()
        self.Window.mainloop()
    
    def login_screen(self):
        self.login = tk.Toplevel()
        setup_window(self.login, "FUV Chatroom Login")
        
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
        self.login.protocol("WM_DELETE_WINDOW", self.Window.destroy)

    def goto_chatroom(self, username):
        if username.strip() == "":
            # Dont allow empty username
            messagebox.showwarning("Warning", "Please input an username")
            return
        elif len(username.strip()) > 9:
            messagebox.showwarning("Warning", "Please input a shorter username")
            return
        
        self.login.destroy()
        self.chatroom_screen(username)
    
    def chatroom_screen(self, username):
        self.Window.deiconify()
        setup_window(self.Window, "FUV Chatroom")
        
        self.username = username
        
        # Configure the root grid: 2 columns (chat area + active list)
        self.Window.grid_columnconfigure(0, weight=3)
        self.Window.grid_columnconfigure(1, weight=1)
        self.Window.grid_rowconfigure(1, weight=1)  # Let the chat area expand vertically

        self.header = tk.Label(self.Window, text="FUV Chatroom", font=(FONT, 14, "bold"))
        self.header.grid(row=0, column=0, sticky="s")
        
        self.user_label = tk.Label(self.Window, text="You: " + username)
        self.user_label.grid(row=0, column=1, sticky="e", padx=10)

        # Row 1: Chat display and active list
        self.chat_display = scrolledtext.ScrolledText(self.Window, wrap=tk.WORD, state="disabled", font = (FONT, 10))
        self.chat_display.grid(row=1, column=0, sticky="nsew", padx=(10, 2), pady=5)

        self.active_frame = tk.Frame(self.Window)
        self.active_frame.grid(row=1, column=1, sticky="nsew", padx=(2, 10), pady=5)
        tk.Label(self.active_frame, text="Active list", font=(FONT, 10, "bold")).pack(anchor="center", padx=5)
        
        self.active_list = tk.Text(self.active_frame, state="disabled", height=20, width=20)
        self.active_list.pack(fill="both", expand=True, padx=5, pady=5)

        #Row 2: Chat entry and send button (column 0 only)
        self.entry_frame = tk.Frame(self.Window)
        self.entry_frame.grid(row=2, column=0, sticky="ew", padx=10)

        self.entry_frame.grid_columnconfigure(0, weight=4)
        self.entry_frame.grid_columnconfigure(1, weight=1)

        self.chat_entry = tk.StringVar()
        
        self.chat_box = tk.Entry(self.entry_frame, textvariable=self.chat_entry)
        self.chat_box.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=2)
        self.chat_box.focus()

        self.send_button = tk.Button(self.entry_frame, text="Send", command = self.send_message)
        self.send_button.grid(row=0, column=1, sticky="ew")
        
        self.chat_box.bind("<Return>", lambda event: self.send_message())

        # Row 3: File and Emotion buttons (column 0 only, equal size)
        self.button_frame = tk.Frame(self.Window)
        self.button_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))

        self.button_frame.grid_columnconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure(1, weight=1)

        self.file_button = tk.Button(self.button_frame, text="File", command = self.upload_file)
        self.file_button.grid(row=0, column=0, sticky="ew")

        self.emoji_button = tk.Button(self.button_frame, text="Emotion", command = self.insert_default_icon)
        self.emoji_button.grid(row=0, column=1, sticky="ew")
        
        self.Window.protocol("WM_DELETE_WINDOW", self.Window.destroy)
    
    def send_message(self):
        raw_msg = self.chat_entry.get()
        # print(self.chat_entry.get())
        
        if raw_msg.strip() == "":
            return

        # Replace emoji text with Unicode
        for code, emoji in EMOJI_DICT.items():
            raw_msg = raw_msg.replace(code, emoji)

        timestamp = datetime.now().strftime("%H:%M:%S")
        if raw_msg.startswith("/w "):
            msg_type = "Private"
        else:
            msg_type = "Global"

        self.display_message(msg_type, self.username, raw_msg, timestamp)
        self.chat_entry.set("")
    
    def display_message(self, msg_type, sender, message, timestamp):
        self.chat_display.config(state="normal")
        tag = "blue" if msg_type == "Global" else "orange"
        formatted = f"({msg_type}) ({sender}) ({timestamp}): {message}\n"
        self.chat_display.insert(tk.END, formatted, tag)
        self.chat_display.tag_config("blue", foreground="blue")
        self.chat_display.tag_config("orange", foreground="darkorange")
        self.chat_display.yview(tk.END)
    
    def upload_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            self.display_system_message(f"Selected file: {filepath.split('/')[-1]}")
            # You would later send this file to the server
    
    def display_system_message(self, message):
        self.chat_display.config(state="normal")
        formatted = f"(System) ({datetime.now().strftime('%H:%M:%S')}): {message}\n"
        self.chat_display.insert(tk.END, formatted, "gray")
        self.chat_display.tag_config("gray", foreground="gray")
        self.chat_display.yview(tk.END)
    
    def insert_default_icon(self):
        emoji_code = ":smile:"
        self.chat_entry.set(self.chat_entry.get() + " " + emoji_code)
    
    def update_user_list(self):
        pass
    
if __name__ == "__main__":
    client = ClientGUI()