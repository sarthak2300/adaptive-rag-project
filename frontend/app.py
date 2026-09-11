"""
Streamlit frontend — UI Layer.
Simple session-based "login" (username as session_id), chat interface,
document upload, and route badge (index/general/search) per answer so the
demo can visibly show which path the agent took.
"""
import os
import sys

# Streamlit runs this file with only frontend/ on sys.path, so the project
# root (where config.py lives) needs to be added manually.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import streamlit as st

from config import settings

st.set_page_config(page_title="Adaptive RAG", page_icon="🤖", layout="wide")

ROUTE_LABEL = {
    "index": "📄 Document (index)",
    "general": "🧠 General knowledge",
    "search": "🌐 Web search",
}


def api_url(path: str) -> str:
    return f"{settings.backend_url}{path}"


# ---------------------------------------------------------------------------
# "Login" (simple username -> session_id, no auth backend needed for a demo)
# ---------------------------------------------------------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if not st.session_state.session_id:
    st.title("🤖 Adaptive RAG — Login")
    username = st.text_input("Enter a username to start / resume your session")
    if st.button("Continue") and username.strip():
        st.session_state.session_id = username.strip()
        st.rerun()
    st.stop()

session_id = st.session_state.session_id

# ---------------------------------------------------------------------------
# Sidebar — document upload + clear
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header(f"👤 {session_id}")
    if st.button("Log out"):
        st.session_state.session_id = None
        st.rerun()

    st.divider()
    st.subheader("📤 Upload a document")
    uploaded = st.file_uploader("PDF or TXT", type=["pdf", "txt", "md"])
    if uploaded and st.button("Ingest document"):
        with st.spinner(
            "Chunking + embedding + storing... (first request after inactivity "
            "can take 1-2 extra minutes while the free backend wakes up)"
        ):
            try:
                resp = requests.post(
                    api_url("/rag/documents/upload"),
                    files={"file": (uploaded.name, uploaded.getvalue())},
                    timeout=300,
                )
                resp.raise_for_status()
                data = resp.json()
                st.success(
                    f"Stored {data['chunks_stored']} chunks from "
                    f"{data['pages_loaded']} page(s) of '{data['file']}'."
                )
            except requests.RequestException as e:
                st.error(f"Upload failed: {e}")

    st.divider()
    st.subheader("🗑️ Documents")
    st.caption(
        "All uploads share one store — old files stay searchable until "
        "cleared. Clear before uploading a new document if you only want "
        "answers from the latest file."
    )
    if st.button("Clear all documents", type="secondary"):
        with st.spinner("Clearing stored documents..."):
            try:
                resp = requests.delete(api_url("/rag/documents"), timeout=30)
                resp.raise_for_status()
                st.success("All stored documents were cleared. Upload a fresh one below.")
            except requests.RequestException as e:
                st.error(f"Clear failed: {e}")

# ---------------------------------------------------------------------------
# Load existing history once per session
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
    try:
        resp = requests.get(api_url(f"/rag/history/{session_id}"), timeout=10)
        if resp.ok:
            st.session_state.messages = resp.json().get("messages", [])
    except requests.RequestException:
        pass  # backend may not be up yet during first load; chat still works

# ---------------------------------------------------------------------------
# Main chat UI
# ---------------------------------------------------------------------------
st.title("🤖 Adaptive RAG Chatbot")
st.caption("Routes each question to: your documents, general knowledge, or live web search.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        route = msg.get("meta", {}).get("route")
        if route:
            st.caption(ROUTE_LABEL.get(route, route))

question = st.chat_input("Ask something...")
if question:
    st.session_state.messages.append({"role": "user", "content": question, "meta": {}})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking... (first request after inactivity can take a minute)"):
            try:
                resp = requests.post(
                    api_url("/rag/query"),
                    json={"question": question, "session_id": session_id},
                    timeout=300,
                )
                resp.raise_for_status()
                data = resp.json()
                st.markdown(data["answer"])
                st.caption(ROUTE_LABEL.get(data["route"], data["route"]))
                if data.get("sources"):
                    with st.expander("Sources"):
                        for s in data["sources"]:
                            st.write(f"- {s}")
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": data["answer"],
                        "meta": {"route": data["route"], "sources": data.get("sources", [])},
                    }
                )
            except requests.RequestException as e:
                st.error(f"Request failed: {e}")