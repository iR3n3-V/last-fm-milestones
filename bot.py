#!/usr/bin/env python3
# bot.py
import os
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

load_dotenv()

GITHUB_REPO = os.getenv("REPO_NAME")
GITHUB_PAT = os.getenv("PAT")
WORKFLOW_FILE = os.getenv("WORKFLOW_FILE", "run.yml")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
USERNAME = "svlaent"  # fisso

if not all([GITHUB_REPO, GITHUB_PAT, TELEGRAM_TOKEN]):
    print("imposta le variabili GITHUB_REPO, GITHUB_PAT, TELEGRAM_TOKEN in .env")
    exit(1)

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
HEADERS = {"Authorization": f"Bearer {GITHUB_PAT}", "Accept": "application/vnd.github+json"}

async def milestone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) == 0:
        await update.message.reply_text("usa: /milestone <art|alb|trk> [count]")
        return
    entity = args[0].lower()
    if entity not in ("art", "alb", "trk"):
        await update.message.reply_text("entity non valida. usa: art | alb | trk")
        return
    count = args[1] if len(args) > 1 else ""
    payload = {
        "ref": "main",
        "inputs": {
            "entity": entity,
            "count": str(count),
            "username": USERNAME
        }
    }
    r = requests.post(API_URL, json=payload, headers=HEADERS)
    if r.status_code == 204:
        await update.message.reply_text("🚀 job avviato! riceverai il risultato su telegram.")
    else:
        await update.message.reply_text(f"errore avvio workflow: {r.status_code} {r.text}")

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("milestone", milestone))
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
