import streamlit as st
import json
from openai import OpenAI

# API-Key laden
api_key = st.secrets.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Seitenlayout
st.set_page_config(page_title="Fehlerlenkung GPT", layout="centered")
st.title("🤖 GPT-gestützter Fehlerlenkungsassistent")

# Benutzerinformationen verwalten
if "user_inputs" not in st.session_state:
    st.session_state.user_inputs = {}

user_inputs = st.session_state.user_inputs

# Begrüßung einmalig anzeigen
if "begruesst" not in st.session_state:
    st.chat_message("assistant").markdown("Hallo! Ich helfe dir bei der Fehlerlenkung im Spritzguss. Lass uns Schritt für Schritt vorgehen.")
    st.session_state.begruesst = True

# Fragenkatalog
fragen = [
    ("name", "Wie darf ich dich nennen?"),
    ("maschine", "An welcher Maschine tritt der Fehler auf?"),
    ("artikelnummer", "Welche Artikelnummer hat das betroffene Teil?"),
    ("auftragsnummer", "Wie lautet die Auftragsnummer?"),
    ("pruefmodus", "Welcher Prüfmodus wird verwendet?"),
    ("fehlerart", "Welche Art von Fehler tritt auf?"),
    ("klassifikation", "Wie wird der Fehler klassifiziert? (kritisch, hauptfehler, nebenfehler)"),
    ("pruefart", "Handelt es sich um eine visuelle oder messende Prüfung?"),
    ("kavitaeten", "Wie viele Kavitäten hat das Werkzeug?")
]

# Nächste offene Frage finden
offene_frage = None
for schluessel, frage in fragen:
    if schluessel not in user_inputs:
        offene_frage = (schluessel, frage)
        break

# Eingabe und Verarbeitung
if prompt := st.chat_input("Antwort eingeben..."):
    if offene_frage:
        feld, _ = offene_frage
        user_inputs[feld] = prompt
        st.chat_message("user").markdown(prompt)

# Frage anzeigen (sofern noch nicht vollständig)
if offene_frage:
    st.chat_message("assistant").markdown(offene_frage[1])
else:
    # Wenn alles ausgefüllt, generiere Zusammenfassung mit GPT
    if "antwort_generiert" not in st.session_state:
        messages = [
            {"role": "system", "content": "Fasse die folgenden Informationen für eine Fehleranalyse im Spritzgussprozess freundlich zusammen."},
            {"role": "user", "content": json.dumps(user_inputs, indent=2)}
        ]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3
        )
        antwort = response.choices[0].message.content
        st.session_state.antwort_generiert = antwort
        st.chat_message("assistant").markdown(antwort)
    else:
        st.chat_message("assistant").markdown(st.session_state.antwort_generiert)
