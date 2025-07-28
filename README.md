# Binance-Announcement-Discord-Webhook-Bot
A bot that uses the Binance Announcements WebSocket API to subscribe to the latest announcements and post them in a Discord channel using a webhook. This script does not require creating a bot and is easy to set up.

# Quickstart
1. Create a .env file.

You can obtain `BINANCE_APIKEY` and `BINANCE_SECRET_KEY` in your [Binance account setting](https://www.binance.com/zh-TC/my/settings/api-management). To create an API key, you need to create a Binance account and complete KYC.

`DISCORD_WEBHOOK_URL` is in the `integration` field channel setting. Create a webhook first, then copy the webhook URL.

`GEMINI_API_KEY` Create one at [Google AI Studio](https://aistudio.google.com/apikey).

`TRANSLATION_PROMPT` For example: "User will enter a segment of English text. Please translate it naturally into Japanese (ja) using expressions commonly used in Japan, and send only the translated text. Note: Do not send anything other than the translation. Do not modify any line breaks or Markdown symbols present in the original text."

2. Run main.py or main.exe.