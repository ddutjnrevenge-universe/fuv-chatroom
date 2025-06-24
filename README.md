# fuv-chatroom
A secure, real-time multi-user chat application with GUI, file sharing, emojis, and encryption.

# Usage
create virtual environment. 


run pip install -r requirements.txt


run rsa_key_generator.py file to create credentials.


run server.py to host server side.


run gui.py in multiple shells for multiple clients.

# 🧩 Chat Application Functional & Technical Specification

## 🔐 User Authentication

- Prompt for username on startup.
- Maintain a list of active usernames.
- **Reject duplicate usernames** with an error popup notification.

---

## 💬 Public Messaging

- Users can send messages broadcasted to **all clients**.
- **Message format:**  
  `(Global) (HH:MM:SS) message content`
- **Encryption:**  
  - Message is encrypted before sending.
  - Decrypted upon receipt.

---

## 📩 Private Messaging

- Triggered by `/w <username> message` OR select from user list.
- **Message format:**  
  `(Private) (From user_name) (HH:MM:SS) message content`
- **Routing:**  
  - Server sends encrypted message **only** to the intended recipient.

---

## 🧍‍♂️ Active User List

- Updates in real-time when users **join** or **leave**.
- GUI reflects the updated list **automatically**.

---

## 🖼️ GUI Requirements

- **Layout:**
  - Scrollable **message window**
  - Scrollable **user list**
  - **Message input field**
- **Auto-scroll:**  
  - Message window scrolls to the latest message **unless user scrolls up manually**.
- **Buttons:**
  - Send
  - Emoji picker
  - File upload
- **Color Coding:**
  - Public messages → Orange
  - Private messages → Blue
- **Error/Info Display:**
  - Incorrect private message syntax
  - File received
  - User joined/left
  - Server disconnect
  - File transfer failure/cancellation
  - Unrecognized emoji code
  - Duplicate username on login
  - Encryption/decryption failure
  - Invalid file type or file too large
  - Private message to non-existent user

---

## 🧪 Stress Test Scenarios

- 100+ messages with varying lengths.
- 50+ users joining simultaneously.
- GUI must remain stable under scrollable overflow.

---

## 🔄 Concurrent Connection

- **Server:** Accepts new client connections via threading.
- **Client:** Listens for incoming messages using a background thread.


---

## 📁 File Sharing

- Select file for transfer.
- Send file metadata + contents in chunks.
- Show **progress/status** (optional).
- Receiver can **accept/reject** download.

---

## 😊 Emoji Support

- Insert emojis via picker or using codes.
- Use mapping table to convert code to emoji Unicode or image.

---

## 🕒 Message Timestamps

- Add timestamp **client-side before encryption**.
- Displayed beside each message in GUI.

---

## 🔒 Encryption

- All message content is **encrypted before sending**.
- Decrypted **on recipient’s side** before GUI display.
- **Keys should be kept private in memory** (no printing/logging).

---

## 🚪 Graceful Exit & Error Handling

- On client exit:
  - Notify server.
  - Remove user from list.
  - Server broadcasts disconnection to all.
- **Catch and log all exceptions.**

