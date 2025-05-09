import json
import streamlit as st
import pandas as pd
from utils import HandleTradeData
from functions import map_agent_func_to_trade_data_handler
from openai import OpenAI

# ──────────────── Ollama-backed OpenAI client ────────────────
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL = "dwightfoster03/functionary-small-v3.1:latest"          # tool-calling model

# ───────────────────── helper utilities ──────────────────────
def _to_openai_messages(history):
    """Convert local chat dicts → OpenAI SDK format."""
    formatted = []
    for m in history:
        role = m["role"]
        base = {"role": role}

        if role == "assistant" and "function_call" in m:
            base |= {"content": None, "function_call": m["function_call"]}
        elif role == "tool":
            base |= {"name": m["name"], "tool_call_id": m["tool_call_id"], "content": m["content"]}
        else:
            base["content"] = m["content"]

        formatted.append(base)
    return formatted


def make_tool_schema(fn_defs):
    """Wrap our function definitions in the new `tools` schema."""
    return [
        {"type": "function", "function": {k: v for k, v in f.items() if k != "callback"}}
        for f in fn_defs
    ]


def call_llm(history, tools=None):
    """Send chat history to the model and return the next message."""
    messages = _to_openai_messages(history)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        response_format={"type": "json_object"},
    )
    msg = resp.choices[0].message
    print("Model response content: " + str(msg.content))

    out = {"role": msg.role, "content": msg.content}
    if msg.tool_calls:
        out["tool_calls"] = [
            {"id": c.id, "name": c.function.name, "arguments": c.function.arguments}
            for c in msg.tool_calls
        ]
    elif msg.function_call:  # legacy fallback
        out["function_call"] = {
            "name": msg.function_call.name,
            "arguments": msg.function_call.arguments,
        }
    return out

# ───────────────────────── Streamlit UI ───────────────────────
st.set_page_config(page_title="PnL Chat Agent", layout="wide")
st.title("📊 Agentic AI – Profit & Loss Analyzer")

upload = st.file_uploader("Upload trade CSV", ["csv"])
if not upload:
    st.stop()

dh = HandleTradeData(upload)
function_defs = map_agent_func_to_trade_data_handler(dh)
tools_schema = make_tool_schema(function_defs)

with st.expander("Full trade log"):
    st.dataframe(dh.df, use_container_width=True)
# with st.expander("Profit & Loss summary"):
#     st.dataframe(dh.pnl_df, use_container_width=True)

display_chat = st.session_state.setdefault("display_chat", [])
chat = st.session_state.setdefault(
    "chat",
    [
        {
            "role": "system",
            "content": (
                "You are a finance assistant. "
                "If you need calculations, call one of the available functions."
            ),
            "display": False,
        }
    ],
)

for m in display_chat:
    # if m.get("display", True):
    st.chat_message(m["role"]).markdown(m["content"])

if question := st.chat_input("Ask about your trades"):
    # ── user question
    display_chat.append({"role": "user", "content": question})
    chat.append({"role": "user", "content": question})
    st.chat_message("user").markdown(question)

    # ── first model pass
    assistant = call_llm(chat, tools=tools_schema)
    if assistant.get("content") and not assistant.get("tool_calls"):
        assistant["display"] = False
        chat.append(assistant)

    # ── new spec: tool_calls array
    if "tool_calls" in assistant:
        print("Tool calls detected: " + str(assistant["tool_calls"]))
        for call in assistant["tool_calls"]:
            fn_name = call["name"]
            args = json.loads(call["arguments"] or "{}")

            fn_entry = next(f for f in function_defs if f["name"] == fn_name)
            result = fn_entry["callback"](**args) if args else fn_entry["callback"]()

            result_md = (
                result.to_markdown(index=False)
                if isinstance(result, pd.DataFrame)
                else str(result)
            )

            chat.append(
                {
                    "role": "tool",
                    "name": fn_name,
                    "tool_call_id": call["id"],
                    "content": result_md,
                    "display": False,
                }
            )

        # second pass for final answer
        assistant = call_llm(chat)
        assistant["display"] = False
        chat.append(assistant)

    # ── legacy 0613 function_call support
    elif "function_call" in assistant:
        fn_name = assistant["function_call"]["name"]
        args = json.loads(assistant["function_call"]["arguments"] or "{}")

        fn_entry = next(f for f in function_defs if f["name"] == fn_name)
        result = fn_entry["callback"](dh.df, **args) if args else fn_entry["callback"](dh.df)

        result_md = (
            result.to_markdown(index=False)
            if isinstance(result, pd.DataFrame)
            else str(result)
        )

        chat.append(
            {"role": "function", "name": fn_name, "content": result_md, "display": False}
        )

        # final answer
        assistant = call_llm(chat)
        assistant["display"] = False
        chat.append(assistant)

    # st.chat_message("assistant").markdown(assistant["content"])
    if assistant["content"]:
        assistant["display"] = True

        try:
            content_data = json.loads(assistant["content"])
            if isinstance(content_data, dict) and content_data:
                if content_data.get("value"):
                    value = content_data["value"]
                    if isinstance(assistant["content"], list):
                        value = "\n".join([str(item) for item in value])
                else:
                    value = next(iter(content_data.values()))
                display_chat.append(
                    {
                        "role": "assistant",
                        "content": value,
                    }
                )
                st.chat_message("assistant").markdown(str(value))
            else:
                st.chat_message("assistant").markdown(assistant["content"])
        except json.JSONDecodeError:
                st.chat_message("assistant").markdown(assistant["content"])
                display_chat.append(
                        {
                            "role": "assistant",
                            "content": assistant["content"],
                        }
                    )
