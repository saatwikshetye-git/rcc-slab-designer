import streamlit as st
from app.ui import main_ui

st.set_page_config(page_title="IS 456 Slab Designer", page_icon="🧱", layout="wide")

def main():
    st.title("🧱 IS 456 Slab Designer")
    st.write("Design one-way and two-way slabs using IS 456 simplified methods.")
    main_ui()

if __name__ == "__main__":
    main()
