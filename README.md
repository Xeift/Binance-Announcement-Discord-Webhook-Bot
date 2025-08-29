# Binance-Announcement-Discord-Webhook-Bot
A bot that uses the Binance Announcements WebSocket API to subscribe to the latest announcements and post them in a Discord channel using a webhook. This script does not require creating a bot and is easy to set up.

# Quickstart
## 1. Create a .env file

| Parameter              | How to Obtain                                                                                                      |
|-----------------------|------------------------------------------------------------------------------------------------------------------|
| `BINANCE_APIKEY` & `BINANCE_SECRET_KEY` | You can obtain them in your [Binance account setting](https://www.binance.com/zh-TC/my/settings/api-management). To create an API key, you need to create a Binance account and complete KYC. |
| `DISCORD_WEBHOOK_URL`  | Located in the `integration` field of the channel setting. Create a webhook first, then copy the webhook URL.      |
| `GEMINI_API_KEY`       | Create one at [Google AI Studio](https://aistudio.google.com/apikey).                                            |
| `TRANSLATION_PROMPT`   | For example: `User will enter a segment of English text. Please translate it naturally into Japanese (ja) using expressions commonly used in Japan, and send only the translated text. Note: Do not send anything other than the translation. Do not modify any line breaks or Markdown symbols present in the original text.` The prompt I personally used is: `使用者會輸入一段幣安的英文原文公告（包括 title 和 body），請你參考公告中的資訊，理解完意思後用繁體中文（zh-TW）和臺灣人常用的用語以正式語氣用 15 行以內的 bulleted list 重寫一個非常精簡的版本（bulletd list 請使用「-」），只保留核心重點的資訊。請注意：這個公告是要傳送到Discord embed 中的，因此請你使用適當的 Markdown。因為 Discord 原生並不支援 Markdown 表格，表格的部分請你用半形space排版後放在多行程式碼區塊中，嚴禁使用 Markdown 表格。另外，公告請只留必要資訊保持簡潔清晰，一些不重要的比如 disclaimer 相關資訊請省略。時區請你換算成 UTC+8（臺北時區）` |


## 2. Run main.py or [main.exe](https://github.com/Xeift/Binance-Announcement-Discord-Webhook-Bot/releases)