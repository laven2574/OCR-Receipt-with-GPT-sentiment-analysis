import streamlit as st

key = st.secrets.get("OPENAI_API_KEY")
st.write("Key loaded:", bool(key))
st.write("Key prefix:", key[:10] if key else None)