import ollama

def query_mistral(model, messages):
    response = ollama.chat(
        model=model,
        messages=messages
    )
    return response['message']['content']
