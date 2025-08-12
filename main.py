# -*- coding: utf-8 -*-
import sys
from flask import Flask, request, jsonify, render_template, stream_with_context, Response
from flask_cors import CORS
import requests
from google.auth import default
from google.auth.transport.requests import Request as GoogleAuthRequest
import json
import redis
import logging
from google.oauth2 import service_account

log_file_path = "/var/www/html/chatbot/chatbot.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

GEMINI_FLASH_ENDPOINT = "https://us-central1-aiplatform.googleapis.com/v1/projects/burmese-chatbot/locations/us-central1/publishers/google/models/gemini-2.0-flash-001:generateContent"
TUNED_MODEL_ENDPOINT = "https://us-central1-aiplatform.googleapis.com/v1/projects/burmese-chatbot/locations/us-central1/endpoints/7733556870962479104:generateContent"

MAX_HISTORY = 10

SYSTEM_PROMPT = """
You are a helpful and polite general-purpose assistant developed by Ooredoo Myanmar.
Support users in Burmese or English on a wide range of topics, including everyday knowledge, helpful advice, and general questions.
If users express frustration or complaints, respond with empathy and professionalism.
Avoid inappropriate content, including hate speech, adult content, or politically sensitive topics.
Always maintain a respectful, friendly, and helpful tone.

Language rule:
- If the user's input contains any Burmese words (even if mixed with English), always reply in Burmese.
- If the input contains only English words, reply in English.
"""

@app.route("/")
def home():
    return render_template("index.html")

def classify_intent_with_gemini(user_input):
    prompt = f"""
You are an intent classifier for a telecom chatbot for Ooredoo Myanmar. Based on the user's message, classify it into one of the following intents:

- balance_transfer
- top up
- Funtone_Activation
- Funtone_Deactivation
- Stop Paygo
- Start Paygo
- Bill Cut off
- Kyo Thone
- packages
- data transfer
- အရမ်းတန်package
- Call me back
- call forwarding
- check balance
- esim
- roaming
- ayan tan
- countries
- ပြည်ပသုံး
- buy pack
- buy packages
- ပက်ကေ့ချ်
- ဒေတာ
- general

Only return one of the two labels: 'general' or 'not general'. Do not include explanations or formatting.

User message: "{user_input}"
"""
    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
    credentials = service_account.Credentials.from_service_account_file(
        "/etc/gcp/credentials.json", scopes=SCOPES
    )
    credentials.refresh(GoogleAuthRequest())
    token = credentials.token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt.strip()}]}]}
    response = requests.post(GEMINI_FLASH_ENDPOINT, headers=headers, json=payload)
    response.raise_for_status()
    result = response.json()
    candidates = result.get("candidates", [])
    if candidates:
        return candidates[0]["content"]["parts"][0]["text"].strip().lower()
    return "general"

def query_vertex_ai_tuned_model(endpoint, payload):
    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
    credentials = service_account.Credentials.from_service_account_file(
        "/etc/gcp/credentials.json", scopes=SCOPES
    )
    credentials.refresh(GoogleAuthRequest())
    token = credentials.token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(endpoint, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def generate_gemini_stream(user_input, user_id):
    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
    credentials = service_account.Credentials.from_service_account_file(
        "/etc/gcp/credentials.json", scopes=SCOPES
    )
    credentials.refresh(GoogleAuthRequest())
    token = credentials.token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    history_key = f"history:{user_id}"
    chat_history = r.lrange(history_key, 0, MAX_HISTORY - 1)
    chat_history_obj = [json.loads(h) for h in chat_history]

    # Prepend system prompt at the beginning
    chat_history_obj.insert(0, {
        "role": "user",
        "parts": [{"text": SYSTEM_PROMPT.strip()}]
    })

    chat_history_obj.append({"role": "user", "parts": [{"text": user_input}]})

    payload = {"contents": chat_history_obj}
    decoder = json.JSONDecoder()
    buffer = ""

    with requests.post(GEMINI_FLASH_ENDPOINT, headers=headers, json=payload, stream=True) as response:
        response.raise_for_status()
        for chunk in response.iter_content(decode_unicode=True):
            if chunk:
                buffer += chunk
                while buffer:
                    try:
                        obj, index = decoder.raw_decode(buffer)
                        buffer = buffer[index:].lstrip()
                        data_items = obj if isinstance(obj, list) else [obj]
                        for item in data_items:
                            candidates = item.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    if "text" in part:
                                        r.lpush(history_key, json.dumps({"role": "model", "parts": [part]}))
                                        r.ltrim(history_key, 0, MAX_HISTORY - 1)
                                        yield f"data: {json.dumps({'response': part['text']})}\n\n"
                    except json.JSONDecodeError:
                        logging.warning("❌ Failed to parse JSON reply: %s", buffer)
                        break

@app.route("/chat", methods=["POST"])
def chat():
    user_input = (request.get_json() or {}).get("message", "")
    user_id = request.remote_addr
    if not user_input:
        return jsonify({"reply": "ကျေးဇူးပြု၍ မေးခွန်းတစ်ခုကို ရေးသားထည့်သွင်းပေးပါ။"})

    try:
        detected_intent = classify_intent_with_gemini(user_input)
        print(f"🔍 Detected intent: {detected_intent}")

        history_key = f"history:{user_id}"
        r.lpush(history_key, json.dumps({"role": "user", "parts": [{"text": user_input}]}))
        r.ltrim(history_key, 0, MAX_HISTORY - 1)

        if detected_intent == "not general":
            prompt = f"{SYSTEM_PROMPT.strip()}\n\nUser: {user_input}\nBot:"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "topP": 0.8,
                    "topK": 40,
                    "maxOutputTokens": 1024
                }
            }

            response_data = query_vertex_ai_tuned_model(TUNED_MODEL_ENDPOINT, payload)
            candidates = response_data.get("candidates", [])
            if not candidates:
                return jsonify({"reply": "ဝန်ဆောင်မှုမှ တုံ့ပြန်မှုမရရှိပါ။"}), 500

            reply_text = candidates[0]["content"]["parts"][0]["text"]
            logging.info("📦 Raw Gemini reply text:%s", reply_text)

            try:
                # Try parsing JSON
                response_json = json.loads(reply_text)
            except json.JSONDecodeError:
                logging.warning("❌ Failed to parse JSON reply: %s", reply_text)
                # Fallback: wrap plain text into valid JSON
                response_json = {"reply": reply_text}

            r.lpush(history_key, json.dumps({"role": "model", "parts": [{"text": reply_text}]}))
            r.ltrim(history_key, 0, MAX_HISTORY - 1)
            return jsonify(response_json)

        else:
            return Response(
                stream_with_context(generate_gemini_stream(user_input, user_id)),
                mimetype='text/event-stream'
            )

    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Request Error: {e}", file=sys.stderr)
        return jsonify({"reply": "အင်တာနက်ချိတ်ဆက်မှုမရှိပါ။"}), 500
    except Exception as e:
        print(f"❌ General Error: {e}", file=sys.stderr)
        return jsonify({"reply": "တစ်ခုခုမှားယွင်းသွားပါသည်။"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
