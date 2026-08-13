import os
from dotenv import load_dotenv
import gradio as gr 
import httpx

load_dotenv()

API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY") 

def extract_message(data: dict) -> str:
    message = ""
    for item in data["output"]:
        if item["type"] == "message":
            for block in item["content"]:
                if block["type"] == "output_text":
                    message += block["text"]
    return message

def user_turn(message, history, previous_response_id):
    payload = {
        "model": "placeholder", 
        "input": [
            {"type": "message", "role": "user", "content": [{"type": "input_text", "text": message}]}
        ],
        "previous_response_id": previous_response_id,
    }
    resp = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    response = extract_message(data)
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response},
    ]
    return history, "", data["id"]  

with gr.Blocks(title="Wazy — Agente de CV") as demo:
    gr.Markdown("## Wazy — Agente de CV de Jesus Huazano")
    chatbot = gr.Chatbot(label="Conversación")
    msg = gr.Textbox(label="Tu pregunta")
    state = gr.State(None)

    msg.submit(user_turn, [msg, chatbot, state], [chatbot, msg, state])

    gr.HTML("""
        <div style="margin-top: 1rem; line-height: 1.6;">
            <strong>Documentación del proyecto:</strong><br>
            <ul>
            <li>
            <a href="https://github.com/Jhuazano-isc/agente-cv" target="_blank" rel="noopener noreferrer"><strong>README completo</strong></a>
            </li>
            </ul>
        </div>
    """)

if __name__ == "__main__":
    demo.launch()