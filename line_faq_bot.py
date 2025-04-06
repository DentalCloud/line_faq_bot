import os
import json
import openai
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 載入環境變數
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
openai.api_key = OPENAI_API_KEY

# 載入 FAQ 資料
with open("faq_data.json", "r", encoding="utf-8") as f:
    faq_data = json.load(f)

# 建立簡單的語意比對函數
def find_best_match(user_input):
    user_input = user_input.lower()
    for item in faq_data:
        if item["question"].lower() in user_input:
            return item["answer"]
    return None

# 儲存每位使用者的最近 5 則訊息
user_histories = {}

def add_to_history(user_id, message):
    history = user_histories.get(user_id, [])
    history.append(message)
    if len(history) > 5:
        history.pop(0)
    user_histories[user_id] = history

@app.route("/")
def home():
    return "DentalCloud FAQ Bot is running."

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_text = event.message.text

    add_to_history(user_id, {"role": "user", "content": user_text})

    # 嘗試從 FAQ 中找答案
    faq_response = find_best_match(user_text)
    if faq_response:
        reply_text = faq_response
    else:
        # 沒找到的話交給 GPT 模型回應
        messages = user_histories.get(user_id, [])
        messages.append({"role": "user", "content": user_text})

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        reply_text = response.choices[0].message["content"]

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
