import streamlit as st
import json
import os
from openai import OpenAI

# OpenAI initialisieren
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Streamlit konfigurieren
st.set_page_config(page_title="Assistent Fehlerlenkung", layout="centered", page_icon="🛠️")

# Modernes CSS
st.markdown('''
    <style>
        body {
            background-color: #f2f4f8;
            font-family: 'Segoe UI', sans-serif;
        }
        .stChatMessage {
            padding: 16px;
            border-radius: 18px;
            margin-bottom: 12px;
            box-shadow: 0 3px 12px rgba(0, 0, 0, 0.04);
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
        .stButton>button {
            border-radius: 6px;
            padding: 10px 24px;
            font-size: 1rem;
            background-color: #1976d2;
            color: white;
            font-weight: bold;
            border: none;
        }
        .stButton>button:hover {
            background-color: #125ea5;
        }
        .block {
            padding: 1rem 0;
            margin-bottom: 2rem;
            border-bottom: 1px solid #e0e0e0;
        }
    </style>
''', unsafe_allow_html=True)

# Titel
st.title("🛠️ Assistent Fehlerlenkung")
st.markdown("### GPT-gestützter Helfer für strukturierte Fehleranalysen & Wiederholprüfungen")
st.markdown("---")

# Fehlerwissen im Hintergrund laden
fehlerwissen_path = "fehlerwissen.json"
if os.path.exists(fehlerwissen_path):
    with open(fehlerwissen_path, "r", encoding="utf-8") as f:
        fehlerwissen = json.load(f)
else:
    fehlerwissen = {}

# Prompts
standard_prompt = (
    "Du bist ein praxisnaher, freundlich kommunizierender Assistent für Schichtleiter im Spritzguss. "
    "Frage schrittweise: Name, Maschine, Artikelnummer, Auftragsnummer, Prüfmodus, Fehlerart, Fehlerklasse (1=kritisch, 2=Hauptfehler, 3=Nebenfehler), "
    "Prüfart (visuell/messend), Kavitätenanzahl. "
    "Wenn Fehlerklasse 1: Maschine sofort stoppen und Schichtleitung informieren. "
    "Wenn nicht kritisch: Schichtleitung informieren, Maschine darf weiterlaufen. "
    "Starte dann die Wiederholprüfung gemäß SP011.2CL02. "
    "Messende Prüfung: 3 Schüsse prüfen – Visuelle Prüfung: 5 Schüsse prüfen. "
    "Grenzwerte: "
    "- Messend: alle Fehlerklassen: 0 Fehler akzeptiert. "
    "- Visuell, kritisch: 0 Fehler akzeptiert. "
    "- Visuell, hauptfehler: <50 Teile = 0 Fehler, ≥50 Teile = max. 3 Fehler. "
    "- Visuell, nebenfehler: <50 Teile = 0 Fehler, ≥50 Teile = max. 7 Fehler. "
    "Wenn nicht i.O.: Material mit SP011.2FO02 sperren, Rückverfolgbarkeit erwähnen, vorherige Paletten prüfen, Instandhaltung informieren. "
    "Schlage danach eine E-Mail an BEQ und Abteilungsleitung vor. "
    "Wenn i.O.: Fehlerlenkung abschließen. Antworte immer menschlich, freundlich und schrittweise."
)

wiederhol_prompt = (
    "Du bist ein praxisnaher Assistent. Starte mit 'Legen wir direkt mit der Wiederholprüfung los.' "
    "Frage nur: Fehlerklasse (1/2/3), Prüfart (visuell oder messend), Kavitätenanzahl. "
    "Messend = 3 Schüsse, visuell = 5 Schüsse. "
    "Wende SP011.2CL02-Grenzwerte an. "
    "Wenn nicht i.O.: Material sperren, Rückverfolgung, E-Mail-Vorschlag an BEQ/AL. "
    "Wenn i.O.: abschließen. Bleib freundlich und klar."
)

# Hilfsfunktionen
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

    # Fehlerwissen im Hintergrund pflegen
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

# Tabs
tab1, tab2 = st.tabs(["🔍 Neuer Fehler", "♻️ Wiederholprüfung"])

if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "standard"

with tab1:
    st.session_state["active_tab"] = "standard"
    st.markdown("#### Neuer Fehlerlenkungsdialog")
    key = "messages_standard"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": standard_prompt}]
    if st.button("🔄 Zurücksetzen Fehler-Dialog"):
        st.session_state[key] = [{"role": "system", "content": standard_prompt}]
        st.success("Fehlerdialog zurückgesetzt.")
    render_chat(st.session_state[key])

with tab2:
    st.session_state["active_tab"] = "wiederhol"
    st.markdown("#### Wiederholprüfung starten")
    key = "messages_wiederhol"
    if key not in st.session_state:
        st.session_state[key] = [{"role": "system", "content": wiederhol_prompt}]
    if st.button("🔄 Zurücksetzen Wiederholprüfung"):
        st.session_state[key] = [{"role": "system", "content": wiederhol_prompt}]
        st.success("Wiederholprüfung zurückgesetzt.")
    render_chat(st.session_state[key])

# Zentrale Chat-Eingabe
user_input = st.chat_input("Antwort eingeben...")
if user_input:
    active = st.session_state.get("active_tab", "standard")
    process_user_input(active, user_input)
