import streamlit as st
import json
import os
from datetime import datetime
from openai import OpenAI

# OpenAI Client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Seite gestalten
st.set_page_config(page_title="Fehlerlenkung GPT", layout="centered")
st.markdown(
    '''
    <style>
        body {background-color: #f4f6f9;}
        .stChatMessage {padding: 12px; border-radius: 16px; margin-bottom: 10px;}
        .stChatMessage.user {background-color: #d1ecf1; color: #004085;}
        .stChatMessage.assistant {background-color: #e2f0cb; color: #3c763d;}
        .stButton>button {
            border-radius: 16px;
            padding: 0.6em 1.2em;
            font-size: 1em;
            background-color: #4a90e2;
            color: white;
            border: none;
        }
        .stButton>button:hover {
            background-color: #357ab8;
            color: white;
        }
    </style>
    ''',
    unsafe_allow_html=True
)

st.title("🧠 GPT-gestützter Fehlerlenkungsassistent")

# Fehlerwissen laden
fehlerwissen_path = "fehlerwissen.json"
if os.path.exists(fehlerwissen_path):
    with open(fehlerwissen_path, "r", encoding="utf-8") as f:
        fehlerwissen = json.load(f)
else:
    fehlerwissen = {}

# Prompts definieren
standard_prompt = (
    "Du bist ein praxisnaher, freundlich kommunizierender Assistent für Schichtleiter im Spritzguss. "
    "Frage schrittweise: Name, Maschine, Artikelnummer, Auftragsnummer, "
    "Prüfmodus ('Bei welchem Prüfmodus wurde der Fehler festgestellt?'), Fehlerart, Fehlerklasse (1=kritisch, 2=Hauptfehler, 3=Nebenfehler), "
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

# Buttons
col1, col2 = st.columns(2)
with col1:
    if st.button("🆕 Neuer Fehler"):
        for key in ["messages", "wiederholpruefung"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
with col2:
    if st.button("🔁 Direkt zur Wiederholprüfung"):
        for key in ["messages", "wiederholpruefung"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.wiederholpruefung = True
        st.rerun()

# Initialisieren
if "messages" not in st.session_state:
    prompt = wiederhol_prompt if st.session_state.get("wiederholpruefung") else standard_prompt
    st.session_state.messages = [{"role": "system", "content": prompt}]

# Chatverlauf
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Eingabe
if prompt := st.chat_input("Antwort eingeben..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=st.session_state.messages,
        temperature=0.3
    )
    reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": reply})
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
