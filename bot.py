"""
Telegram Bot — logs user commands to Google Sheets.

Setup:
  1. Put your Telegram bot token in the TELEGRAM_BOT_TOKEN environment variable.
  2. Put your Google Service Account JSON key file contents in the
     GOOGLE_SERVICE_ACCOUNT_JSON environment variable  (the full JSON as a string),
     OR place the file at telegram-bot/credentials.json and the bot will load it from disk.
  3. Put the target Google Spreadsheet ID in the GOOGLE_SHEET_ID environment variable.
     (The ID is the long string between /d/ and /edit in the sheet URL.)
  4. Share the spreadsheet with the service account email (client_email in the JSON)
     and grant it Editor access.

Commands:
  /mnp [tariff] [form] [phone] [name]              -> sheet: mnp
  /b2b [tariff] [phone] [name]                     -> sheet: b2b
  /phone [brand] [price] [IMEI] [phone] [puk] [name] -> sheet: phone
  /migr [tariff] [phone] [name]                    -> sheet: migr
  /new [tariff] [phone] [name]                     -> sheet: new
  /22 [phone] [puk] [form] [name]                  -> sheet: 22
"""

import os
import json
import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

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
    """Return an authorised gspread client using service-account credentials."""
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)


def get_worksheet(sheet_name: str) -> gspread.Worksheet:
    """Return the named worksheet, creating it with headers if absent."""
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
        logger.info("Created worksheet '%s' with headers.", sheet_name)

    return worksheet


def append_row(sheet_name: str, values: list) -> None:
    """Prepend today's date and append a row to the given sheet."""
    row = [today()] + values
    ws = get_worksheet(sheet_name)
    ws.append_row(row, value_input_option="USER_ENTERED")
    logger.info("Appended to '%s': %s", sheet_name, row)


def parse_args(context: ContextTypes.DEFAULT_TYPE, expected: int) -> list | None:
    """Return a list of exactly `expected` string arguments or None."""
    args = context.args or []
    if len(args) != expected:
        return None
    return list(args)


async def reply_error(update: Update, usage: str) -> None:
    await update.message.reply_text(f"Usage: {usage}")


async def reply_ok(update: Update, sheet: str) -> None:
    await update.message.reply_text(f"Saved to sheet \"{sheet}\".")


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_mnp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /mnp [tariff] [form] [phone] [name]
    Sheet: mnp | Headers: date, tariff, form, phone, name
    """
    args = parse_args(context, 4)
    if args is None:
        await reply_error(update, "/mnp [tariff] [form] [phone] [name]")
        return
    tariff, form, phone, name = args
    try:
        append_row("mnp", [tariff, form, phone, name])
        await reply_ok(update, "mnp")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data. Please try again.")


async def cmd_b2b(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /b2b [tariff] [phone] [name]
    Sheet: b2b | Headers: date, tariff, phone, name
    """
    args = parse_args(context, 3)
    if args is None:
        await reply_error(update, "/b2b [tariff] [phone] [name]")
        return
    tariff, phone, name = args
    try:
        append_row("b2b", [tariff, phone, name])
        await reply_ok(update, "b2b")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data. Please try again.")


async def cmd_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /phone [brand] [price] [IMEI] [phone] [puk] [name]
    Sheet: phone | Headers: date, brand, price, IMEI, phone, puk, name
    """
    args = parse_args(context, 6)
    if args is None:
        await reply_error(update, "/phone [brand] [price] [IMEI] [phone] [puk] [name]")
        return
    brand, price, imei, phone, puk, name = args
    try:
        append_row("phone", [brand, price, imei, phone, puk, name])
        await reply_ok(update, "phone")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data. Please try again.")


async def cmd_migr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /migr [tariff] [phone] [name]
    Sheet: migr | Headers: date, tariff, phone, name
    """
    args = parse_args(context, 3)
    if args is None:
        await reply_error(update, "/migr [tariff] [phone] [name]")
        return
    tariff, phone, name = args
    try:
        append_row("migr", [tariff, phone, name])
        await reply_ok(update, "migr")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data. Please try again.")


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /new [tariff] [phone] [name]
    Sheet: new | Headers: date, tariff, phone, name
    """
    args = parse_args(context, 3)
    if args is None:
        await reply_error(update, "/new [tariff] [phone] [name]")
        return
    tariff, phone, name = args
    try:
        append_row("new", [tariff, phone, name])
        await reply_ok(update, "new")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data. Please try again.")


async def cmd_22(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /22 [phone] [puk] [form] [name]
    Sheet: 22 | Headers: date, phone, puk, form, name
    """
    args = parse_args(context, 4)
    if args is None:
        await reply_error(update, "/22 [phone] [puk] [form] [name]")
        return
    phone, puk, form, name = args
    try:
        append_row("22", [phone, puk, form, name])
        await reply_ok(update, "22")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("Error saving data. Please try again.")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Available commands:\n\n"
        "/mnp [tariff] [form] [phone] [name]\n"
        "/b2b [tariff] [phone] [name]\n"
        "/phone [brand] [price] [IMEI] [phone] [puk] [name]\n"
        "/migr [tariff] [phone] [name]\n"
        "/new [tariff] [phone] [name]\n"
        "/22 [phone] [puk] [form] [name]\n\n"
        "Separate all arguments with spaces. "
        "Each command saves a row (with today's date) to its own sheet tab."
    )
    await update.message.reply_text(text)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("mnp",   cmd_mnp))
    app.add_handler(CommandHandler("b2b",   cmd_b2b))
    app.add_handler(CommandHandler("phone", cmd_phone))
    app.add_handler(CommandHandler("migr",  cmd_migr))
    app.add_handler(CommandHandler("new",   cmd_new))
    app.add_handler(CommandHandler("22",    cmd_22))

    logger.info("Bot is starting…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
