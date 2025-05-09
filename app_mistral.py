import json, os, streamlit as st, pandas as pd
from utils import HandleTradeData     # your own helpers
from functions import map_agent_func_to_trade_data_handler                     # the list above
from ollama import chat                                 # ollama-python client

MODEL_NAME = "mistral"     # whatever tag you pulled

def ollama_chat(messages, functions=None):
    """Wrapper that preserves OpenAI-compatible keys."""
    return chat(
        model=MODEL_NAME,
        messages=messages,
        functions=functions,
        stream=False,
    )

# ─────────────────────── Streamlit UI ──────────────────────────
st.set_page_config(page_title="PnL Chat Agent", layout="wide")
st.title("📊 Agentic AI – Profit & Loss Analyzer")

upload = st.file_uploader("Upload trade CSV", ["csv"])
if not upload:
    st.stop()

dh = HandleTradeData(upload)  # ↳ clean Amount inside this helper
function_defs = map_agent_func_to_trade_data_handler(dh)  # ↳ map functions to methods
pnl_df = dh.pnl_df

with st.expander("Full trade log"):
    st.dataframe(dh.df)
st.subheader("PnL summary"); st.dataframe(pnl_df)

# keep chat history
if "chat" not in st.session_state:
    st.session_state.chat = [
        {"role": "system",
         "content": (
             "You are a finance assistant. "
             "If you need calculations, call an available tool."
         )}
    ]

for m in st.session_state.chat:
    st.chat_message(m["role"]).markdown(m["content"])

if user_q := st.chat_input("Ask about your trades"):
    # 1️⃣ append user question
    st.session_state.chat.append({"role": "user", "content": user_q})

    # 2️⃣ first round: let the model decide to answer or call a tool
    resp = ollama_chat(
        messages=st.session_state.chat,
        functions=[{k: v for k, v in f.items() if k != "callback"} for f in function_defs],
    )

    # Ollama returns dict; mimic OpenAI JSON
    assistant_msg = resp["message"]
    st.session_state.chat.append(assistant_msg)

    # 3️⃣ if the model chose a function, execute & send the result back
    if assistant_msg.get("function_call"):
        fn_name = assistant_msg["function_call"]["name"]
        args    = json.loads(assistant_msg["function_call"]["arguments"] or "{}")

        # run the matching python callback
        fn_entry = next(f for f in function_defs if f["name"] == fn_name)
        result   = fn_entry["callback"](dh.df, **args) if args else fn_entry["callback"](dh.df)

        # serialise DataFrame results so the model can read them
        if isinstance(result, pd.DataFrame):
            result_str = result.to_markdown(index=False)
        else:
            result_str = str(result)

        # function => tool message
        func_msg = {
            "role": "function",
            "name": fn_name,
            "content": result_str,
        }
        st.session_state.chat.append(func_msg)

        # second round: let the model craft the final answer
        final_resp = ollama_chat(messages=st.session_state.chat)
        assistant_msg = final_resp["message"]
        st.session_state.chat.append(assistant_msg)

    # 4️⃣ render assistant reply
    st.chat_message("assistant").markdown(assistant_msg["content"])
