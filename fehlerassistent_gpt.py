import streamlit as st
import json
import os
from openai import OpenAI

# OpenAI Client initialisieren
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Seite konfigurieren
st.set_page_config(page_title="Fehlerlenkungs-GPT", layout="centered", page_icon="🧠")

# Modernes UI
st.markdown('''
    <style>
        body {
            background-color: #f7f9fc;
            font-family: 'Segoe UI', sans-serif;
        }
        .stChatMessage {
            padding: 14px;
            border-radius: 18px;
            margin-bottom: 12px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            max-width: 80%;
        }
        .stChatMessage.user {
            background-color: #e3f2fd;
            color: #0d47a1;
            margin-left: auto;
        }
        .stChatMessage.assistant {
            background-color: #e8f5e9;
            color: #1b5e20;
            margin-right: auto;
        }
    </style>
''', unsafe_allow_html=True)

# Fehlerwissen laden oder initialisieren
fehlerwissen_path = "fehlerwissen.json"
if os.path.exists(fehlerwissen_path):
    with open(fehlerwissen_path, "r", encoding="utf-8") as f:
        fehlerwissen = json.load(f)
else:
    fehlerwissen = {}

# Prompts
standard_prompt = "Du bist ein praxisnaher Assistent... (gekürzt hier)"
wiederhol_prompt = "Du bist ein praxisnaher Assistent... (gekürzt hier)"

# Chatlogik
def render_chat(messages):
    for msg in messages[1:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

def process_user_input(tab_key, user_input):
    session_key = f"messages_{tab_key}"
    messages = st.session_state.get(session_key, [])
    messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.3
    )
    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    st.session_state[session_key] = messages

    with st.chat_message("assistant"):
        st.markdown(reply)

    for line in reply.splitlines():
        if "Fehlerart:" in line and "Prüfart:" in reply:
            art = line.split("Fehlerart:")[-1].strip()
            if art not in fehlerwissen:
                if "visuell" in reply.lower():
                    fehlerwissen[art] = "visuell"
                elif "messend" in reply.lower():
                    fehlerwissen[art] = "messend"
    with open(fehlerwissen_path, "w", encoding="utf-8") as f:
        json.dump(fehlerwissen, f, ensure_ascii=False, indent=2)

# Tabs definieren
tab1, tab2 = st.tabs(["🔍 Neuer Fehler", "♻️ Wiederholprüfung"])

if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "standard"

with tab1:
    st.session_state["active_tab"] = "standard"
    st.subheader("🧾 Neuer Fehler")
    key = "messages_standard"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": standard_prompt}]
    if st.button("🔄 Zurücksetzen (Fehler)"):
        st.session_state[key] = [{"role": "system", "content": standard_prompt}]
        st.success("Fehlerdialog zurückgesetzt.")
    render_chat(st.session_state[key])

with tab2:
    st.session_state["active_tab"] = "wiederhol"
    st.subheader("♻️ Wiederholprüfung")
    key = "messages_wiederhol"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": wiederhol_prompt}]
    if st.button("🔄 Zurücksetzen (Wiederholprüfung)"):
        st.session_state[key] = [{"role": "system", "content": wiederhol_prompt}]
        st.success("Wiederholprüfung zurückgesetzt.")
    render_chat(st.session_state[key])

# Fehlerwissen anzeigen
with st.expander("📘 Fehlerwissen anzeigen/bearbeiten"):
    st.json(fehlerwissen)

# EINZIGES zentrales chat_input
user_input = st.chat_input("Antwort eingeben...")
if user_input:
    active = st.session_state.get("active_tab", "standard")
    process_user_input(active, user_input)
