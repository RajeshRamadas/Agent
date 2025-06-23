import requests
import json

url = "https://api.awanllm.com/v1/chat/completions"
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer 724621ab-c587-477a-9550-2ec03916fd49'
}

model_name = "Meta-Llama-3-8B-Instruct"
chat_history = [{"role": "system", "content": "You are a helpful assistant."}]

while True:
    user_input = input("You: ")
    if user_input.lower() in {"exit", "quit"}:
        break

    chat_history.append({"role": "user", "content": user_input})

    payload = {
        "model": model_name,
        "messages": chat_history,
        "repetition_penalty": 1.1,
        "temperature": 0.7,
        "top_p": 0.9,
        "top_k": 40,
        "max_tokens": 1024,
        "stream": True
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload), stream=True)
    print("Assistant:", end=" ", flush=True)
    assistant_response = ""

    for line in response.iter_lines(decode_unicode=True):
        if line and line.startswith("data: "):
            try:
                data = json.loads(line.lstrip("data: "))
                content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                assistant_response += content
                print(content, end="", flush=True)
            except json.JSONDecodeError:
                continue

    print()
    chat_history.append({"role": "assistant", "content": assistant_response})
