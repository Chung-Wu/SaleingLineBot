import os
import sys
import userdata
from flask import Flask, jsonify, request, abort, send_file
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from fsm import TocMachine
from utils import send_text_message
from userdata import User

load_dotenv()
    
machine = TocMachine(
    states=[
        "user", 
        "purchase_bread",
        "shopping_list",
        "purchase_cake",
        "confirm",
        "menu"
        ],
    transitions=[
        {
            "trigger": "advance",
            "source": ["user", "purchase_bread", "shopping_list", "menu", "purchase_cake", "confirm"],
            "dest": "menu",
            "conditions": "is_going_to_menu",
        },
        {
            "trigger": "advance",
            "source": ["user", "menu", "purchase_bread", "purchase_cake"],
            "dest": "purchase_bread",
            "conditions": "is_going_to_purchase_bread",
        },
        {
            "trigger": "advance",
            "source": ["user", "purchase_bread", "menu", "purchase_cake"],
            "dest": "purchase_cake",
            "conditions": "is_going_to_purchase_cake",
        },
        {
            "trigger": "advance",
            "source": ["purchase_bread", "menu", "purchase_cake"],
            "dest": "shopping_list",
            "conditions": "is_going_to_shopping_list",
        },
        {
            "trigger": "advance",
            "source": ["purchase_bread", "shopping_list", "menu", "user"],
            "dest": "confirm",
            "conditions": "is_going_to_confirm",
        },
        {
            "trigger": "go_back",
            "source": ["purchase_bread", "shopping_list", "confirm", "purchase_cake"],
            "dest": "user"
        },
        
    ],
    initial="user",
    auto_transitions=False,
    show_conditions=True,
)

app = Flask(__name__, static_url_path="")


# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv("LINE_CHANNEL_SECRET", None)
channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", None)
if channel_secret is None:
    print("Specify LINE_CHANNEL_SECRET as environment variable.")
    sys.exit(1)
if channel_access_token is None:
    print("Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.")
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue

        line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=event.message.text)
        )
 
    return "OK"


@app.route("/webhook", methods=["POST"])
def webhook_handler():
    signature = request.headers["X-Line-Signature"]
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            continue
        if not isinstance(event.message, TextMessage):
            continue
        if not isinstance(event.message.text, str):
            continue
        print(f"\nFSM STATE: {machine.state}")
        print(f"REQUEST BODY: \n{body}")
        response = machine.advance(event)
        
        if response == False:
            send_text_message(event.reply_token, "錯誤\n溫馨提醒:若要重新開始請輸入menu")

    return "OK"


@app.route("/show-fsm", methods=["GET"])
def show_fsm():
    
    machine.get_graph().draw("fsm.png", prog="dot", format="png")
    return send_file("fsm.png", mimetype="image/png")

if __name__ == "__main__":
    port = os.environ.get("PORT", 8000)
    app.run(host="0.0.0.0", port=port, debug=True)
