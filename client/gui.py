import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from datetime import datetime
from emoji_dict import EMOJI_DICT

class ChatClientGUI:
    def __init__(self, root, username="Guest"):
        self.root = root
        self.root.title("FUV Chatroom")
        self.root.minsize(900, 600)  # Set a larger minimum window size

        self.username = username
        self.setup_gui()

    def setup_gui(self):
        # Configure grid weights for resizing
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_columnconfigure(2, weight=1)

        # Top layout
        self.chat_label = tk.Label(self.root, text="FUV Chatroom", bg="midnight blue", fg="white", font=("Arial", 20, "bold"))
        self.chat_label.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.user_label = tk.Label(self.root, text="Active", bg="midnight blue", fg="white", font=("Arial", 16))
        self.user_label.grid(row=0, column=2, sticky="ew")

        # Chat box
        self.chat_box = scrolledtext.ScrolledText(self.root, width=80, height=28, state="disabled", font=("Arial", 14))
        self.chat_box.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        # Active user list
        self.user_list = tk.Listbox(self.root, width=28, height=28, font=("Arial", 14))
        self.user_list.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")

        # Entry box
        self.entry_var = tk.StringVar()
        self.entry_box = tk.Entry(self.root, textvariable=self.entry_var, width=75, font=("Arial", 14))
        self.entry_box.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        # Send button
        self.send_btn = tk.Button(self.root, text="➤", bg="DarkGoldenrod1", font=("Arial", 16), command=self.send_message)
        self.send_btn.grid(row=2, column=1, sticky="w")

        # Bind Enter key to send message
        self.entry_box.bind("<Return>", lambda event: self.send_message())

        # File and Emoji Buttons
        self.file_btn = tk.Button(self.root, text="📎", font=("Arial", 16), command=self.select_file)
        self.file_btn.grid(row=3, column=0, sticky="w", padx=10)

        self.emoji_btn = tk.Button(self.root, text="😊", font=("Arial", 16), command=self.insert_emoji)
        self.emoji_btn.grid(row=3, column=0, sticky="w", padx=60)

        # Exit protocol
        self.root.protocol("WM_DELETE_WINDOW", self.graceful_exit)

    def insert_emoji(self):
        emoji_code = ":smile:"
        self.entry_var.set(self.entry_var.get() + " " + emoji_code)

    def select_file(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            self.display_system_message(f"Selected file: {filepath.split('/')[-1]}")
            # You would later send this file to the server

    def send_message(self):
        raw_msg = self.entry_var.get()
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
        formatted = f"(System) ({datetime.now().strftime('%H:%M:%S')}): {message}\n"
        self.chat_box.insert(tk.END, formatted, "gray")
        self.chat_box.tag_config("gray", foreground="gray")
        self.chat_box.config(state="disabled")
        self.chat_box.yview(tk.END)

    def update_user_list(self, user_list):
        self.user_list.delete(0, tk.END)
        for user in user_list:
            self.user_list.insert(tk.END, f"● {user}")

    def graceful_exit(self):
        # TODO: send disconnect message to server
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatClientGUI(root, username="FUV-User-1")
    # Example user list update
    app.update_user_list(["FUV-User-1", "FUV-User-2", "FUV-User-3"])
    root.mainloop()
