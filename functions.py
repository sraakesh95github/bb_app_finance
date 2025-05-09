def default_handler():
    return "I may not be having the necessary tool to give an accurate answer on that question."

FUNCTION_DEFS = [
    {
        "name": "calculate_profit_for_instrument",
        "description": "Return the total (realised) profit or loss for a single symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "instrument": {"type": "string", "description": "Ticker / option root"}
            },
            "required": ["instrument"],
        },
        "callback": default_handler,   # will be invoked by Streamlit
    },
    {
        "name": "get_max_transaction",
        "description": "Largest absolute Amount value in the trade log (positive or negative).",
        "parameters": {"type": "object", "properties": {}},
        "callback": default_handler,
    },
    {
        "name": "calculate_ach_transactions_sum",
        "description": "Sum of all ACH transactions.",
        "parameters": {"type": "object", "properties": {}},
        "callback": default_handler,
    },
    {
        "name": "calculate_exp_loss_percentage",
        "description": "Calculate the percentage of expiration loss.",
        "parameters": {"type": "object", "properties": {}},
        "callback": default_handler,
    },

    {
        "name": "risk_management_advice",
        "description": "give risk management advice based on the trade log.",
        "parameters": {"type": "object", "properties": {}},
        "callback": default_handler,
    }
]

def map_agent_func_to_trade_data_handler(data_handler):
    """Map the function names to the data handler methods."""
    FUNCTION_DEFS[0]["callback"] = data_handler.get_amount_for_instrument
    FUNCTION_DEFS[1]["callback"] = data_handler.get_max_amount_for_instrument
    FUNCTION_DEFS[2]["callback"] = data_handler.calculate_ach_transactions_sum
    FUNCTION_DEFS[3]["callback"] = data_handler.calculate_exp_loss_percentage
    FUNCTION_DEFS[4]["callback"] = data_handler.risk_management_advice
    return FUNCTION_DEFS

