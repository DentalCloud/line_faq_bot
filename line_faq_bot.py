import os
import json
from flask import Flask, request, abort
from dotenv import load_dotenv
from openai import OpenAI
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 載入環境變數
load_dotenv()

# 初始化
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 載入 FAQ 資料
with open("faq_data.json", "r", encoding="utf-8") as f:
    faq_data = json.load(f)

# 儲存用戶對話紀錄
user_histories = {}

def get_recent_history(user_id):
    return user_histories.get(user_id, [])

def update_user_history(user_id, role, content):
    history = user_histories.get(user_id, [])
    history.append({"role": role, "content": content})
    if len(history) > 5:
        history = history[-5:]  # 保留最近 5 則對話
    user_histories[user_id] = history

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
    user_message = event.message.text

    # 更新對話紀錄
    update_user_history(user_id, "user", user_message)

    # 建立完整訊息歷史（加上 system 設定）
    messages = [{"role": "system", "content": "你是 DentalCloud 的客服助理，請根據 FAQ 資料回覆用戶的問題，若資料不足請友善引導他們留下聯絡方式以安排醫師回覆。"}]
    messages.extend(get_recent_history(user_id))

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    reply = response.choices[0].message.content.strip()

    # 儲存助手回覆
    update_user_history(user_id, "assistant", reply)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run()
