import streamlit as st
import json
import os
from datetime import datetime
from openai import OpenAI

# OpenAI Client initialisieren
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Seite konfigurieren
st.set_page_config(page_title="Fehlerlenkungs-GPT", layout="centered", page_icon="🧠")

# Custom CSS für modernes UI
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
        .stButton > button {
            border-radius: 8px;
            background-color: #1976d2;
            color: white;
            padding: 10px 20px;
            font-weight: bold;
            border: none;
        }
        .stButton > button:hover {
            background-color: #1565c0;
        }
    </style>
''', unsafe_allow_html=True)

# Titel
st.title("🧠 Fehlerlenkungs-GPT Assistent")
st.caption("Ein Assistent für Schichtleiter zur strukturierten Fehleranalyse und Wiederholprüfung")

# Tabs für Navigation
tab1, tab2 = st.tabs(["🔍 Neuer Fehler", "♻️ Wiederholprüfung"])

# Fehlerwissen laden oder initialisieren
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

# Funktion zur Chatlogik
def chat_interface(prompt, start_key="standard"):
    if f"messages_{start_key}" not in st.session_state:
        st.session_state[f"messages_{start_key}"] = [{"role": "system", "content": prompt}]

    # Chatverlauf anzeigen
    for msg in st.session_state[f"messages_{start_key}"][1:]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Eingabe
    if user_input := st.chat_input("Antwort eingeben..."):
        st.session_state[f"messages_{start_key}"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=st.session_state[f"messages_{start_key}"],
            temperature=0.3
        )
        reply = response.choices[0].message.content
        st.session_state[f"messages_{start_key}"].append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

        # Fehlerwissen aktualisieren
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

# Tab 1: Neuer Fehler
with tab1:
    st.info("Starte einen neuen Fehlerlenkungsdialog.")
    if st.button("🔄 Alles zurücksetzen"):
        if "messages_standard" in st.session_state:
            del st.session_state["messages_standard"]
        st.experimental_rerun()
    chat_interface(standard_prompt, start_key="standard")

# Tab 2: Wiederholprüfung
with tab2:
    st.warning("Starte direkt mit der Wiederholprüfung.")
    if st.button("🔄 Wiederholprüfung zurücksetzen"):
        if "messages_wiederhol" in st.session_state:
            del st.session_state["messages_wiederhol"]
        st.experimental_rerun()
    chat_interface(wiederhol_prompt, start_key="wiederhol")

# Fehlerwissen anzeigen
with st.expander("📘 Fehlerwissen anzeigen/bearbeiten"):
    st.json(fehlerwissen)
