import os
from telegram.ext import Application, CommandHandler
from flask import Flask, request

telegram_token = os.getenv("TELEGRAM_TOKEN")
app = Application.builder().token(telegram_token).build()

# comandi esempio
async def start(update, context):
    await update.message.reply_text("ciao!")

app.add_handler(CommandHandler("start", start))

# server flask
server = Flask(__name__)

@server.post(f"/{telegram_token}")
def webhook():
    data = request.get_json(force=True)
    app.update_queue.put_nowait(app._parse_update(data))
    return "ok", 200

if __name__ == "__main__":
    import asyncio
    from telegram import Bot

    bot = Bot(token=telegram_token)
    url = os.getenv("WEBHOOK_URL")  # es: https://nome-progetto.onrender.com

    asyncio.run(bot.set_webhook(f"{url}/{telegram_token}"))

    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
