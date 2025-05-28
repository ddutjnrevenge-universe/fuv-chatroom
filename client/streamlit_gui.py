# import streamlit as st
# from datetime import datetime
# from emoji_dict import EMOJI_DICT  # Use your updated emoji dictionary

# # Session state init
# if "chat_log" not in st.session_state:
#     st.session_state.chat_log = []

# if "user_list" not in st.session_state:
#     st.session_state.user_list = ["FUV-User-1", "FUV-User-2", "FUV-User-3"]

# if "username" not in st.session_state:
#     st.session_state.username = "FUV-User-1"

# # --- Layout ---
# st.set_page_config(page_title="FUV Chatroom", layout="wide")
# st.title("💬 FUV Chatroom")

# # Chat columns
# chat_col, users_col = st.columns([3, 1])

# with chat_col:
#     st.subheader("Chat")
#     chat_display = st.empty()
#     with st.form("send_form", clear_on_submit=True):
#         message_input = st.text_input(
#             "Type a message", ""
#         )
#         file = st.file_uploader("📎 Upload a file", type=None, label_visibility="collapsed")

#         # Submit buttons
#         submitted = st.form_submit_button("➤ Send")

#         if submitted:

#             if message_input.strip():
#                 # Replace emoji text with Unicode
#                 for code, emoji in EMOJI_DICT.items():
#                     message_input = message_input.replace(code, emoji)

#                 timestamp = datetime.now().strftime("%H:%M:%S")
#                 msg_type = "Private" if message_input.startswith("/w ") else "Global"
#                 formatted = f"({msg_type}) ({st.session_state.username}) ({timestamp}): {message_input}"
#                 st.session_state.chat_log.append((msg_type, formatted))

#                 # Handle file uploads
#                 if file:
#                     st.session_state.chat_log.append(
#                         ("System", f"(System) ({timestamp}): {file.name} uploaded.")
#                     )


# # --- Display Chat Log ---
# with chat_col:
#     with chat_display.container():
#         for msg_type, msg in st.session_state.chat_log:
#             color = "blue" if msg_type == "Global" else "orange" if msg_type == "Private" else "gray"
#             st.markdown(f"<span style='color:{color}'>{msg}</span>", unsafe_allow_html=True)

# # --- User List ---
# with users_col:
#     st.subheader("Active Users")
#     for user in st.session_state.user_list:
#         st.markdown(f"🟢 **{user}**")

import streamlit as st
from datetime import datetime
from emoji_dict import EMOJI_DICT  # Use your updated emoji dictionary

# --- Setup ---
st.set_page_config(page_title="💬 FUV Chatroom", layout="wide")
st.markdown(
    """
    <style>
    .message-bubble {
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 15px;
        max-width: 80%;
        word-wrap: break-word;
    }
    .global { background-color: #e6f4ff; color: #00196E; }
    .private { background-color: #fcf1dc; color: #FFAD1D; }
    .system { background-color: #f0f0f0; color: gray; font-style: italic; }
    .username { font-weight: bold; }
    .timestamp { font-size: 0.8em; color: gray; margin-left: 8px; }
    .own { text-align: right; margin-left: auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- State ---
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

if "user_list" not in st.session_state:
    st.session_state.user_list = ["FUV-User-1", "FUV-User-2", "FUV-User-3"]

if "username" not in st.session_state:
    st.session_state.username = "FUV-User-1"

# --- Layout ---
st.title("💬 FUV Chatroom")
chat_col, users_col = st.columns([4, 1])

# --- Chat Area ---
with chat_col:
    st.subheader("🗣️ Messages")
    chat_display = st.container()

    with st.form("send_form", clear_on_submit=True):
        message_input = st.text_input("Type your message (e.g., Hi :smile:)", "")
        file = st.file_uploader("📎 Upload file", label_visibility="collapsed")

        submitted = st.form_submit_button("➤ Send")

        if submitted and message_input.strip():
            # Emoji replace
            for code, emoji in EMOJI_DICT.items():
                message_input = message_input.replace(code, emoji)

            timestamp = datetime.now().strftime("%H:%M:%S")
            msg_type = "Private" if message_input.startswith("/w ") else "Global"
            formatted_msg = f"{message_input}"
            st.session_state.chat_log.append({
                "type": msg_type,
                "sender": st.session_state.username,
                "timestamp": timestamp,
                "message": formatted_msg,
                "own": True,
            })

            if file:
                file_msg = f"📎 {file.name} uploaded."
                st.session_state.chat_log.append({
                    "type": "System",
                    "sender": "System",
                    "timestamp": timestamp,
                    "message": file_msg,
                    "own": True,
                })

# --- Display Messages ---
with chat_display:
    for entry in st.session_state.chat_log:
        bubble_class = entry["type"].lower()
        alignment = "own" if entry.get("own") else ""
        sender = entry["sender"]
        timestamp = entry["timestamp"]
        message = entry["message"]

        html = f"""
        <div class="message-bubble {bubble_class} {alignment}" style="padding:5px 9px; font-size:0.95em; max-width:65%;">
            <span class="username">{sender}</span>
            <span class="timestamp">({timestamp})</span><br>
            {message}
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

# --- User List ---
with users_col:
    st.subheader("👥 Active Users")
    for user in st.session_state.user_list:
        st.markdown(f"🟢 **{user}**")
