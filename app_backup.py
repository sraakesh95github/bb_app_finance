import streamlit as st
from utils import load_trades, calculate_pnl
from agent import query_mistral

st.set_page_config(page_title="PnL Chat Agent", layout="wide")
st.title("📊 Agentic AI - Profit & Loss Analyzer")

uploaded_file = st.file_uploader("Upload trade CSV", type=["csv"])

if uploaded_file:
    df = load_trades(uploaded_file)
    pnl_df = calculate_pnl(df)

    st.subheader("Calculated Profit & Loss:")
    st.dataframe(pnl_df)

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    st.subheader("💬 Ask about your trades")
    user_input = st.text_input("Ask a question", key="input")

    if user_input:
        st.session_state["messages"].append({"role": "user", "content": user_input})

        # Append trade summary to prompt
        context  = f"""You are analyzing trading data. Here is the full transaction log:
        {df.to_string(index=False)}

        And here is the profit/loss summary grouped by Instrument:
        {pnl_df.to_string(index=False)}
        """
        full_prompt = f"You are a financial assistant. Given the following PnL data:\n\n{context}\n\nAnswer the question: {user_input}"

        response = query_mistral(full_prompt)
        st.session_state["messages"].append({"role": "assistant", "content": response})

    for msg in st.session_state["messages"]:
        st.chat_message(msg["role"]).markdown(msg["content"])
