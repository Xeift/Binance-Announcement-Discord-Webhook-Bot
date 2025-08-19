import base64
import datetime
import hashlib
import hmac
import json
import os
import random
import string
import threading
import time
from datetime import datetime, timezone
from typing import List

import websocket
from discord import Embed, SyncWebhook
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()
API_KEY = os.getenv('BINANCE_APIKEY')
SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TRANSLATION_PROMPT = os.getenv('TRANSLATION_PROMPT')
TOPIC = 'com_announcement_en'
RECV_WINDOW = 30000
BASE_URI = 'wss://api.binance.com/sapi/wss'


def generate_random_string(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def build_signed_url():
    timestamp = int(time.time() * 1000)
    random_str = generate_random_string()
    
    params = {
        'random': random_str,
        'topic': TOPIC,
        'recvWindow': RECV_WINDOW,
        'timestamp': timestamp
    }

    query_string = '&'.join(f'{k}={params[k]}' for k in sorted(params))
    
    signature = hmac.new(
        SECRET_KEY.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    signed_params = f'{query_string}&signature={signature}'
    return f'{BASE_URI}?{signed_params}'

def start_ping(ws):
    def run():
        while True:
            time.sleep(30)
            try:
                ws.send('PING')
            except Exception as e:
                print(f'[Ping Error] {e}')
                break
    threading.Thread(target=run, daemon=True).start()

class TranslationSchema(BaseModel):
    translated_content: str

def translate(original_text):
    client = genai.Client(api_key=GEMINI_API_KEY)
    model = "gemini-2.0-flash-lite"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=original_text),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TranslationSchema,
        system_instruction=[
            types.Part.from_text(text=TRANSLATION_PROMPT),
        ],
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    
    return response.parsed.translated_content  


def on_message(ws, message):
    try:
        msg = json.loads(message)
        if msg.get('type') == 'DATA' and msg.get('topic') == TOPIC:
            raw_data = msg.get('data')
            announcement = json.loads(raw_data)
            webhook = SyncWebhook.from_url(DISCORD_WEBHOOK_URL)
            translated_text = translate(announcement['body'])

            embed = Embed(title=announcement['title'], color=0xF0B90B, description=translated_text[:2000])
            embed.add_field(name='Category', value=announcement['catalogName'], inline=False)
            print('----------       New announcement found!     ----------')
            print(raw_data)
            print()
            print(translated_text)
            print('----------       New announcement found!     ----------')
            embed.timestamp = datetime.fromtimestamp(announcement['publishDate'] / 1000, tz=timezone.utc)
            embed.set_footer(
                text='Source: Binance WebSocket API. Translated by Google Gemini API.',
                icon_url='https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Binance_Logo.svg/127px-Binance_Logo.svg.png'
            )
            webhook.send(embed=embed)


    except Exception as e:
        print(f'[Message Parsing Error] {e}\noriginal message: {message}')

def on_error(ws, error):
    print(f'[WebSocket Error] {error}')

def on_close(ws, close_status_code, close_msg):
    print(f'[WebSocket Closed] Code: {close_status_code}, Msg: {close_msg}')

def on_open(ws):
    print('[WebSocket Opened] Connected to server')
    subscribe_msg = {
        'command': 'SUBSCRIBE',
        'value': TOPIC
    }
    ws.send(json.dumps(subscribe_msg))
    start_ping(ws)

def connect():
    while True:
        try:
            ws_url = build_signed_url()
            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                header={'X-MBX-APIKEY: ' + API_KEY}
            )
            ws.run_forever()
        except Exception as e:
            print(f'[Reconnection Error] {e}')
        print('[Reconnecting in 5 seconds...]')
        time.sleep(5)

if __name__ == '__main__':
    connect()
