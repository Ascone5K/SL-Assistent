import streamlit as st
import json
import pandas as pd
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
        .stChatMessage {padding: 10px; border-radius: 12px;}
        .stChatMessage.user {background-color: #e0f7fa;}
        .stChatMessage.assistant {background-color: #f1f8e9;}
        .stButton>button {
            border-radius: 12px;
            padding: 0.5em 1em;
            font-size: 1em;
            background-color: #90caf9;
            color: black;
        }
        .stButton>button:hover {
            background-color: #64b5f6;
            color: white;
        }
    </style>
    ''',
    unsafe_allow_html=True
)

st.title("🤖 Fehlerlenkungsassistent für den Schichtleiter")

# Buttons modern
col1, col2 = st.columns(2)
with col1:
    if st.button("🆕 Neuer Fehler"):
        for key in ["messages", "antwort_generiert", "user_inputs", "begruesst", "wiederholpruefung"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
with col2:
    if st.button("🔁 Direkt zur Wiederholprüfung"):
        st.session_state["wiederholpruefung"] = True
        for key in ["messages", "antwort_generiert", "user_inputs", "begruesst"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Fehlerwissen laden
fehlerwissen_path = "fehlerwissen.json"
if os.path.exists(fehlerwissen_path):
    with open(fehlerwissen_path, "r", encoding="utf-8") as f:
        fehlerwissen = json.load(f)
else:
    fehlerwissen = {}

# Systemprompt definieren
standard_prompt = (
    "Du bist ein praxisnaher, freundlich kommunizierender Assistent für Schichtleiter im Spritzguss. "
    "Starte jede Konversation mit: 'Hallo, wie kann ich dich unterstützen?' "
    "Frage dann nacheinander: Name, Maschine, Artikelnummer, Auftragsnummer, "
    "Prüfmodus (Formulierung: 'Bei welchem Prüfmodus wurde der Fehler festgestellt?'), Fehlerart, Fehlerklasse (1=kritisch, 2=Hauptfehler, 3=Nebenfehler), "
    "Prüfart (visuell/messend), Kavitätenanzahl. "
    "Wenn Fehlerklasse 1: Maschine sofort stoppen und Schichtleitung informieren. "
    "Wenn nicht kritisch: Schichtleitung informieren, Maschine darf weiterlaufen. "
    "Starte dann die Wiederholprüfung gemäß SP011.2CL02. "
    "Gib klare, freundliche Anweisungen wie: 'Gut, machen wir eine Wiederholprüfung…'. "
    "Messende Prüfung: 3 Schüsse prüfen – Visuelle Prüfung: 5 Schüsse prüfen. "
    "Grenzwerte: "
    "- Messend: alle Fehlerklassen: 0 Fehler akzeptiert. "
    "- Visuell, kritisch: 0 Fehler akzeptiert. "
    "- Visuell, hauptfehler: <50 Teile = 0 Fehler, ≥50 Teile = max. 3 Fehler. "
    "- Visuell, nebenfehler: <50 Teile = 0 Fehler, ≥50 Teile = max. 7 Fehler. "
    "Wenn nicht i.O.: Material mit SP011.2FO02 sperren, Rückverfolgbarkeit erwähnen, auch vorherige Paletten prüfen, Instandhaltung informieren. "
    "Erstelle anschließend automatisch einen Vorschlag für eine kurze E-Mail an BEQ und Abteilungsleitung mit allen relevanten Informationen. "
    "Wenn i.O.: Fehlerlenkung abschließen. Sprich menschlich, natürlich und reagiere auf Antworten kontextbezogen."
)

wiederhol_prompt = (
    "Starte direkt mit einer Wiederholprüfung nach SP011.2CL02. "
    "Frage nur: Fehlerklasse (1,2,3), Prüfart (visuell oder messend), Kavitätenanzahl. "
    "Gib konkrete Prüfanweisung: "
    "- messend: 3 Schüsse prüfen – visuell: 5 Schüsse prüfen. "
    "Wende Grenzwerte an und beurteile: i.O. oder nicht i.O. "
    "Wenn nicht i.O.: Erstelle automatisch eine kurze E-Mail-Vorlage für BEQ und Abteilungsleitung. "
    "Sprich klar, freundlich und hilf dem Schichtleiter Schritt für Schritt."
)

# Initialisieren + Begrüßung
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": wiederhol_prompt if st.session_state.get("wiederholpruefung") else standard_prompt}
    ]
    if "begruesst" not in st.session_state:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=st.session_state.messages,
            temperature=0.3
        )
        begruessung = response.choices[0].message.content
        st.session_state.messages.append({"role": "assistant", "content": begruessung})
        st.session_state.begruesst = True
        with st.chat_message("assistant"):
            st.markdown(begruessung)

# Chatverlauf anzeigen
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Nutzereingabe
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
