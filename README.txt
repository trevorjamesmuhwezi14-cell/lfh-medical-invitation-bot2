# LFH Medical Telegram Personal Invitation Bot — Free Render Webhook Version

This version is designed for a Render FREE WEB SERVICE. It uses Telegram webhooks instead of long-running polling.

## Telegram workflow
1. Send /start to the bot.
2. Tap Create Personal Invitation.
3. Enter a guest name such as Dr John Doe.
4. The bot returns the LFH invitation image with the name inserted.

## Render settings
Service type: Web Service
Language: Python 3
Build command: pip install -r requirements.txt
Start command: python bot.py
Plan: Free
Environment variable:
BOT_TOKEN = your private BotFather token

Render automatically supplies PORT and RENDER_EXTERNAL_URL. The bot uses these to listen for HTTPS webhook requests and register the Telegram webhook.

## Security
Never publish BOT_TOKEN in GitHub, screenshots, or chat. Store it only as a Render environment variable.

## Free-tier note
Render Free web services can spin down after 15 minutes without inbound traffic. Telegram webhook traffic wakes the service when an update arrives, so the first interaction after sleeping can take about a minute.
