import datetime
import hashlib
import hmac
import json
import os
import random
import string
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import websocket
from discord import Embed, SyncWebhook
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

load_dotenv()
API_KEY = os.getenv('BINANCE_API_KEY')
SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')
CODEX_BIN = os.getenv('CODEX_BIN', 'codex')
CODEX_MODEL = os.getenv('CODEX_MODEL', 'gpt-6.1-sol')
TRANSLATION_PROMPT = os.getenv('TRANSLATION_PROMPT')
TOPIC = 'com_announcement_en'
RECV_WINDOW = 30000
BASE_URI = 'wss://api.binance.com/sapi/wss'


category_mapping = ''
# category_mapping = {
#     'category_local': '類別',
#     'New Cryptocurrency Listing': '新上架加密貨幣',
#     'Latest Binance News': '幣安最新動態',
#     'Latest Activities': '最新活動',
#     'New Fiat Listings': '新上架法幣',
#     'API Updates': '幣安 API 更新',
#     'Maintenance Updates': '維護更新',
#     'Crypto Airdrop': '空投',
#     'Delisting': '下架資訊'
# }

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
    model_config = ConfigDict(extra='forbid')

    translated_title: str
    translated_body: str

def translate(original_text):
    if not TRANSLATION_PROMPT:
        raise ValueError('Missing required environment variable: TRANSLATION_PROMPT')

    prompt = (
        f'{TRANSLATION_PROMPT}\n\n'
        'Return the translated title and body in the required JSON format.\n\n'
        f'Announcement:\n{original_text}'
    )
    with tempfile.TemporaryDirectory(prefix='binance-translation-') as temp_dir:
        schema_path = Path(temp_dir) / 'schema.json'
        output_path = Path(temp_dir) / 'translation.json'
        schema_path.write_text(json.dumps(TranslationSchema.model_json_schema()), encoding='utf-8')

        result = subprocess.run(
            [
                CODEX_BIN, 'exec',
                '--model', CODEX_MODEL,
                '--sandbox', 'read-only',
                '--skip-git-repo-check',
                '--ephemeral',
                '-c', 'forced_login_method="chatgpt"',
                '-c', 'model_reasoning_effort="low"',
                '--output-schema', str(schema_path),
                '--output-last-message', str(output_path),
                '--color', 'never',
                '-',
            ],
            input=prompt,
            cwd=temp_dir,
            env={key: value for key, value in os.environ.items() if key not in {'OPENAI_API_KEY', 'CODEX_API_KEY'}},
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f'codex exec failed ({result.returncode}): {result.stderr.strip()}')

        translation = TranslationSchema.model_validate_json(output_path.read_text(encoding='utf-8'), strict=True)
    return (translation.translated_title, translation.translated_body)


def on_message(ws, message):
    try:
        msg = json.loads(message)
        if msg.get('type') == 'DATA' and msg.get('topic') == TOPIC:
            raw_data = msg.get('data')
            announcement = json.loads(raw_data)
            webhook = SyncWebhook.from_url(DISCORD_WEBHOOK_URL)
            (translated_title, translated_body) = translate(f'"title": {announcement["title"]}, "body": {announcement["body"]}')

            embed = Embed(title=translated_title, color=0xF0B90B, description=translated_body[:2000])
            if category_mapping:
                embed.add_field(name=category_mapping['category_local'], value=category_mapping[announcement['catalogName']], inline=False)
            else:
                embed.add_field(name='Category', value=announcement['catalogName'], inline=False)

            print('----------       New announcement found!     ----------')
            print(announcement['title'])
            print(raw_data)
            print('----------       New announcement found!     ----------')
            embed.timestamp = datetime.fromtimestamp(announcement['publishDate'] / 1000, tz=timezone.utc)
            embed.set_footer(
                text=f'Source: Binance WebSocket API. Translated by {CODEX_MODEL}.',
                icon_url='https://bin.bnbstatic.com/static/images/common/logo.png'
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
