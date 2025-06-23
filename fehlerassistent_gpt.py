import streamlit as st
import json
import pandas as pd
import os
from datetime import datetime
from openai import OpenAI

# OpenAI API
api_key = st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Layout
st.set_page_config(page_title="Fehlerlenkung GPT", layout="centered")
st.title("🤖 Fehlerlenkungsassistent")

# Button: Neuer Fehler
if st.button("🆕 Neuer Fehler"):
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

# Verlauf
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": (
            "Du bist ein interaktiver Assistent für Fehlerlenkung im Spritzgussprozess. "
            "Stelle Schritt für Schritt die relevanten Fragen: Name, Maschine, Artikelnummer, Auftragsnummer, Prüfmodus, "
            "Fehlerart, Klassifikation, Prüfart, Kavitätenanzahl. "
            "Führe danach durch die Entscheidung 'kritischer Fehler?' und leite, falls nötig, die Wiederholprüfung nach "
            "SP011.2CL02 ein. Erläutere dem Schichtleiter wie viele Schüsse geprüft werden müssen, ab wann negativ, "
            "und leite anschließend passende Sofortmaßnahmen ein. Wenn BEQ informiert werden muss, erstelle eine kurze "
            "E-Mail-Zusammenfassung. Sprich klar, freundlich, natürlich und frage bei Unklarheiten nach. "
            "Lerne bei Bedarf Fehlerarten und Prüfarten hinzu."
        )}
    ]

# Bisherige Nachrichten anzeigen
for msg in st.session_state.messages[1:]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Eingabe und Verarbeitung
if prompt := st.chat_input("Antwort eingeben..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # GPT-Antwort
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=st.session_state.messages,
        temperature=0.3
    )
    reply = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)

    # Automatisches Lernen von Fehlerarten
    for line in reply.splitlines():
        if "Fehlerart:" in line and "Prüfart:" in reply:
            art = line.split("Fehlerart:")[-1].strip()
            if art not in fehlerwissen:
                if "visuelle" in reply.lower():
                    fehlerwissen[art] = "visuell"
                elif "messende" in reply.lower():
                    fehlerwissen[art] = "messend"
    with open(fehlerwissen_path, "w", encoding="utf-8") as f:
        json.dump(fehlerwissen, f, ensure_ascii=False, indent=2)

    # CSV speichern nach abgeschlossener Erfassung
    if "antwort_generiert" not in st.session_state and "kavitätenanzahl" in prompt.lower():
        daten = {}
        for m in st.session_state.messages:
            if m["role"] == "user":
                daten["Eingabe"] = m["content"]
            elif m["role"] == "assistant" and "Zusammenfassung" in m["content"]:
                daten["GPT-Zusammenfassung"] = m["content"]

        daten["Zeitstempel"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df_neu = pd.DataFrame([daten])
        csv_path = "fehlerfaelle.csv"
        if os.path.exists(csv_path):
            df_alt = pd.read_csv(csv_path)
            df_kombi = pd.concat([df_alt, df_neu], ignore_index=True)
        else:
            df_kombi = df_neu
        df_kombi.to_csv(csv_path, index=False)
