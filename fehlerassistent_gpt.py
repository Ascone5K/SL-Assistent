import streamlit as st
import json
import pandas as pd
import os
from datetime import datetime
from openai import OpenAI

# OpenAI Client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Seite einrichten
st.set_page_config(page_title="Fehlerlenkung GPT", layout="centered")
st.title("🤖 Fehlerlenkungsassistent für den Schichtleiter")

# Buttons
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
    "Du bist ein natürlich sprechender, hilfsbereiter Assistent für Schichtleiter im Spritzguss. "
    "Beginne das Gespräch mit einer freundlichen Begrüßung. "
    "Frage nacheinander folgende Informationen ab: Name, Maschine, Artikelnummer, Auftragsnummer, "
    "Prüfmodus ('Bei welchem Prüfmodus wurde der Fehler festgestellt?'), Fehlerart, Fehlerklasse (1=kritisch, 2=Hauptfehler, 3=Nebenfehler), "
    "Prüfart (visuell/messend), Kavitätenanzahl. "
    "Wenn Fehlerklasse 1: Maschine sofort stoppen und Schichtleitung informieren. "
    "Wenn nicht kritisch: Schichtleitung informieren, Maschine läuft weiter. "
    "Führe danach die Wiederholprüfung gemäß SP011.2CL02 durch. "
    "Sag z. B.: 'Gut, machen wir eine Wiederholprüfung um sicherzustellen, ob der Fehler systematisch ist.' "
    "Leite den Prüfer durch: 'Bitte entnimm 3 aufeinanderfolgende Schüsse mit jeweils X Kavitäten...' "
    "Bewerte anhand der Grenzwerte: bei >7 Fehlern ist die Wiederholprüfung nicht i.O. "
    "Wenn nicht i.O.: Material mit SP011.2FO02 sperren, Rückverfolgbarkeit sicherstellen, vorherige Paletten prüfen, Instandhaltung informieren. "
    "Wenn i.O.: Fehlerlenkung abschließen. "
    "Sei klar, praxisnah und freundlich. Gib nie mehrere Fragen auf einmal aus. "
    "Schlage bei Bedarf eine Mail an BEQ und Abteilungsleitung vor."
)

wiederhol_prompt = (
    "Starte direkt eine Wiederholprüfung gemäß SP011.2CL02. "
    "Frage nur die notwendigen Informationen ab: Fehlerklasse, Prüfart (visuell/messend), Kavitätenanzahl. "
    "Erkläre den Ablauf praxisnah und sprich natürlich. "
    "Ziel: Prüfen, ob Fehler systematisch ist, und dem Schichtleiter klare Handlungsempfehlungen geben."
)

# Initialisierung
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": wiederhol_prompt if st.session_state.get("wiederholpruefung") else standard_prompt}
    ]

# Nachrichten anzeigen
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Eingabe
if prompt := st.chat_input("Antwort eingeben..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # GPT-Antwort abrufen
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=st.session_state.messages,
        temperature=0.3
    )
    reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": reply})
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
