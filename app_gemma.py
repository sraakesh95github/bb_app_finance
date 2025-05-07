import json, streamlit as st, pandas as pd
from utils import HandleTradeData
from functions import map_agent_func_to_trade_data_handler
from openai import OpenAI

# ─────────────────────  Ollama-backed client  ──────────────────────
client = OpenAI(
    base_url="http://localhost:11434/v1",  # Ollama REST
    api_key="ollama",                      # any non-empty string
)

MODEL = "gemma3:latest"          # ← 1️⃣  NEW MODEL TAG

def call_llm(messages, functions=None, function_call="auto"):
    """
    Wrapper that:  • passes our tool schema • forces JSON mode
    Returns a plain dict Streamlit can render.
    """
    # print("Functions: " + str(functions))
    print("Messages: " + str(messages))
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        functions=functions,               # OpenAI 0613 schema
        function_call=function_call,              # ← 2️⃣  force valid-JSON replies
        response_format={"type": "json", "stream": False},  # ← 3️⃣  no streaming
    )
    print("Message: " + str(resp.choices[0].message))
    m = resp.choices[0].message
    out = {"role": m.role, "content": m.content}
    if m.function_call:
        out["function_call"] = {
            "name": m.function_call.name,
            "arguments": m.function_call.arguments,
        }
    return out

# ─────────────────────  Streamlit UI  ─────────────────────
st.set_page_config(page_title="PnL Chat Agent", layout="wide")
st.title("📊 Agentic AI – Profit & Loss Analyzer")

upload = st.file_uploader("Upload trade CSV", ["csv"])
if not upload:
    st.stop()

dh            = HandleTradeData(upload)
function_defs = map_agent_func_to_trade_data_handler(dh)
pnl_df        = dh.pnl_df

with st.expander("Full trade log"):
    st.dataframe(dh.df)
with st.expander("Profit & Loss log"):
    st.dataframe(pnl_df)

chat = st.session_state.setdefault(
    "chat",
    [{"role": "system",
      "content": (
          "You are a finance assistant. "
          "If you need calculations, call one of the available functions."
      )}],
)

for msg in chat:
    st.chat_message(msg["role"]).markdown(msg["content"])

if question := st.chat_input("Ask about your trades"):
    # user message
    chat.append({"role": "user", "content": question})
    st.chat_message("user").markdown(question)

    # first pass – Hermes may answer or request a tool
    fn_schemas = [{k: v for k, v in f.items() if k != "callback"} for f in function_defs]
    assistant  = call_llm(chat, functions=fn_schemas)
    chat.append(assistant)

    # tool call?
    if "function_call" in assistant:
        fn_name = assistant["function_call"]["name"]
        args    = json.loads(assistant["function_call"]["arguments"] or "{}")

        fn_entry = next(f for f in function_defs if f["name"] == fn_name)
        result   = fn_entry["callback"](dh.df, **args) if args else fn_entry["callback"](dh.df)
        result_md = result.to_markdown(index=False) if isinstance(result, pd.DataFrame) else str(result)

        chat.append({"role": "function", "name": fn_name, "content": result_md})

        # second pass – let the model craft the final answer
        assistant = call_llm(chat)
        chat.append(assistant)

    st.chat_message("assistant").markdown(assistant["content"])
