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
    # Render передает порт в переменную окружения PORT
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
logger = logging.getLogger(name)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_HEADERS = {
    "mnp":   ["date", "tariff", "form", "phone", "name"],
    "b2b":   ["date", "tariff", "phone", "name"],
    "phone": ["date", "brand", "price", "IMEI", "phone", "puk", "name"],
    "migr":  ["date", "tariff", "phone", "name"],
    "new":   ["date", "tariff", "phone", "name"],
    "22":    ["date", "phone", "puk", "form", "name"],
}

def today() -> str:
    return datetime.now().strftime("%d-%m-%Y")

def get_gspread_client() -> gspread.Client:
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        # Исправлено: file вместо file
        creds_path = os.path.join(os.path.dirname(file), "credentials.json")
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)

def get_worksheet(sheet_name: str) -> gspread.Worksheet:
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEET_ID environment variable is not set.")

    client = get_gspread_client()
    spreadsheet = client.open_by_key(sheet_id)

    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=sheet_name, rows=1000, cols=len(SHEET_HEADERS[sheet_name])
        )
        worksheet.append_row(SHEET_HEADERS[sheet_name])
        logger.info(f"Created worksheet '{sheet_name}' with headers.")
    return worksheet

def append_row(sheet_name: str, values: list) -> None:
    row = [today()] + values
    ws = get_worksheet(sheet_name)
    ws.append_row(row, value_input_option="USER_ENTERED")
    logger.info(f"Appended to '{sheet_name}': {row}")

def parse_args(context: ContextTypes.DEFAULT_TYPE, expected: int) -> list | None:
    args = context.args or []
    if len(args) != expected:
        return None
    return list(args)

async def reply_error(update: Update, usage: str) -> None:
    await update.message.reply_text(f"Usage: {usage}")

async def reply_ok(update: Update, sheet: str) -> None:
    await update.message.reply_text(f"Saved to sheet \"{sheet}\".")


async def cmd_mnp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_args(context, 4)
    if args is None:
        await reply_error(update, "/mnp [tariff] [form] [phone] [name]")
        return
    try:
        append_row("mnp", args)
        await reply_ok(update, "mnp")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_b2b(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_args(context, 3)
    if args is None:
        await reply_error(update, "/b2b [tariff] [phone] [name]")
        return
    try:
        append_row("b2b", args)
        await reply_ok(update, "b2b")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")
async def cmd_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_args(context, 6)
    if args is None:
        await reply_error(update, "/phone [brand] [price] [IMEI] [phone] [puk] [name]")
        return
    try:
        append_row("phone", args)
        await reply_ok(update, "phone")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_migr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_args(context, 3)
    if args is None:
        await reply_error(update, "/migr [tariff] [phone] [name]")
        return
    try:
        append_row("migr", args)
        await reply_ok(update, "migr")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_args(context, 3)
    if args is None:
        await reply_error(update, "/new [tariff] [phone] [name]")
        return
    try:
        append_row("new", args)
        await reply_ok(update, "new")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_22(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = parse_args(context, 4)
    if args is None:
        await reply_error(update, "/22 [phone] [puk] [form] [name]")
        return
    try:
        append_row("22", args)
        await reply_ok(update, "22")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data.")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Available commands:\n\n"
        "/mnp [tariff] [form] [phone] [name]\n"
        "/b2b [tariff] [phone] [name]\n"
        "/phone [brand] [price] [IMEI] [phone] [puk] [name]\n"
        "/migr [tariff] [phone] [name]\n"
        "/new [tariff] [phone] [name]\n"
        "/22 [phone] [puk] [form] [name]"
    )
    await update.message.reply_text(text)

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")

    # Запускаем Flask в отдельном потоке
    keep_alive()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("mnp",   cmd_mnp))
    app.add_handler(CommandHandler("b2b",   cmd_b2b))
    app.add_handler(CommandHandler("phone", cmd_phone))
    app.add_handler(CommandHandler("migr",  cmd_migr))
    app.add_handler(CommandHandler("new",   cmd_new))
    app.add_handler(CommandHandler("22",    cmd_22))

    logger.info("Bot is starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if name == "main":
    main()