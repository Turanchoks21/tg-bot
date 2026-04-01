import os
import json
import logging
from datetime import datetime
from threading import Thread

import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = {
    "mnp": ["date", "tariff", "form", "phone", "name"],
    "b2b": ["date", "tariff", "phone", "name"],
    "phone": ["date", "brand", "price", "IMEI", "phone", "puk", "name"],
    "migr": ["date", "tariff", "phone", "name"],
    "new": ["date", "tariff", "phone", "name"],
    "22": ["date", "phone", "puk", "form", "name"],
}

def today() -> str:
    return datetime.now().strftime("%d-%m-%Y")

def get_gspread_client() -> gspread.Client:
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)

def get_worksheet(sheet_name: str) -> gspread.Worksheet:
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID is not set.")
    client = get_gspread_client()
    spreadsheet = client.open_by_key(sheet_id)
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=sheet_name, rows=1000, cols=len(SHEET_HEADERS[sheet_name])
        )
        worksheet.append_row(SHEET_HEADERS[sheet_name])
    return worksheet

def append_row(sheet_name: str, values: list) -> None:
    row = [today()] + values
    ws = get_worksheet(sheet_name)
    ws.append_row(row, value_input_option="USER_ENTERED")

async def cmd_mnp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) != 4:
        await update.message.reply_text("Usage: /mnp [tariff] [form] [phone] [name]")
        return
    try:
        append_row("mnp", list(args))
        await update.message.reply_text("Saved to mnp")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_b2b(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) != 3:
        await update.message.reply_text("Usage: /b2b [tariff] [phone] [name]")
        return
    try:
        append_row("b2b", list(args))
        await update.message.reply_text("Saved to b2b")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) != 6:
        await update.message.reply_text("Usage: /phone [brand] [price] [IMEI] [phone] [puk] [name]")
        return
    try:
        append_row("phone", list(args))
        await update.message.reply_text("Saved to phone")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_migr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) != 3:
        await update.message.reply_text("Usage: /migr [tariff] [phone] [name]")
        return
    try:
        append_row("migr", list(args))
        await update.message.reply_text("Saved to migr")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) != 3:
        await update.message.reply_text("Usage: /new [tariff] [phone] [name]")
        return
    try:
        append_row("new", list(args))
        await update.message.reply_text("Saved to new")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_22(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if len(args) != 4:
        await update.message.reply_text("Usage: /22 [phone] [puk] [form] [name]")
        return
    try:
        append_row("22", list(args))
        await update.message.reply_text("Saved to 22")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Bot started! Use /mnp, /b2b, /phone, /migr, /new, or /22")

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set.")
    keep_alive()
    app_tg = Application.builder().token(token).build()
    app_tg.add_handler(CommandHandler("start", cmd_start))
    app_tg.add_handler(CommandHandler("mnp", cmd_mnp))
    app_tg.add_handler(CommandHandler("b2b", cmd_b2b))
    app_tg.add_handler(CommandHandler("phone", cmd_phone))
    app_tg.add_handler(CommandHandler("migr", cmd_migr))
    app_tg.add_handler(CommandHandler("new", cmd_new))
    app_tg.add_handler(CommandHandler("22", cmd_22))
    logger.info("Bot is starting...")
    app_tg.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()