import streamlit as st
import pandas as pd
import openai
import json
from datetime import datetime
import uuid
import os

st.write("Vorhandene Secrets:", dict(st.secrets))
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Systemverhalten
system_prompt = """Du bist ein freundlicher, praxisnaher Fehlerlenkungsassistent im Spritzguss. Du führst Schichtleiter Schritt für Schritt durch die Fehlermeldung. Du fragst nach: Name, Maschine, Artikelnummer, Auftragsnummer, Prüfmodus, Fehlerart, Klassifikation, Prüfart, Kavitätenanzahl. Du bewertest Wiederholprüfungen gemäß SP011.2CL02. Du gibst klare Anweisungen und generierst am Ende eine Zusammenfassung + E-Mail-Vorschlag an BEQ. Wenn dir eine Fehlerart nicht bekannt ist, fragst du: 'Ist das eine visuelle oder messende Prüfung?' und merkst dir die Antwort. Sprich natürlich, klar und hilfsbereit.
"""

# Verlauf speichern
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": system_prompt}
    ]

# Lade Lernwissen
try:
    with open("fehlerwissen.json", "r", encoding="utf-8") as f:
        fehlerwissen = json.load(f)
except FileNotFoundError:
    fehlerwissen = {}

# Layout
st.set_page_config(page_title="Fehlerlenkung GPT", layout="centered")
st.title("🤖 GPT-gestützter Fehlerlenkungsassistent")

# Verlauf anzeigen
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Eingabe
if prompt := st.chat_input("Antwort eingeben..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # GPT antworten lassen
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=st.session_state.messages,
        temperature=0.3
    )

    gpt_reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": gpt_reply})
    with st.chat_message("assistant"):
        st.markdown(gpt_reply)

    # Fehlerart automatisch klassifizieren
    for line in gpt_reply.splitlines():
        if "Fehlerart:" in line:
            art = line.split("Fehlerart:")[-1].strip()
            if art not in fehlerwissen:
                if "visuell" in gpt_reply:
                    fehlerwissen[art] = "visuell"
                elif "messend" in gpt_reply:
                    fehlerwissen[art] = "messend"
    with open("fehlerwissen.json", "w", encoding="utf-8") as f:
        json.dump(fehlerwissen, f, ensure_ascii=False, indent=2)
