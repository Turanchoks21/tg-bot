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

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

SHEET_HEADERS = {
    "mnp":   ["date", "tariff", "form", "phone", "name"],
    "b2b":   ["date", "tariff", "phone", "name"],
    "phone": ["date", "brand", "price", "IMEI", "phone", "puk", "name"],
    "migr":  ["date", "tariff", "phone", "name"],
    "new":   ["date", "tariff", "phone", "name"],
    "22":    ["date", "phone", "puk", "form", "name"],
}

def get_gspread_client():
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    else:
        creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)

def append_row_smart(sheet_name, values):
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    client = get_gspread_client()
    ss = client.open_by_key(sheet_id)
    
    try:
        ws = ss.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=sheet_name, rows=1000, cols=10)
        ws.append_row(SHEET_HEADERS[sheet_name])
    
    # Считаем заполненные строки только по первому столбцу (Дата)
    # Это позволяет игнорировать формулы в соседних столбцах
    col_a = ws.col_values(1)
    next_row = len(col_a) + 1
    
    row_data = [datetime.now().strftime("%d-%m-%Y")] + list(values)
    
    # Определяем диапазон записи (например, A10:E10)
    num_cols = len(row_data)
    end_col = chr(ord('A') + num_cols - 1)
    range_label = f"A{next_row}:{end_col}{next_row}"
    
    ws.update(range_name=range_label, values=[row_data], value_input_option="USER_ENTERED")

async def cmd_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cmd = update.message.text.split()[0][1:].lower()
    args = context.args or []
    
    if cmd not in SHEET_HEADERS:
        return

    expected = len(SHEET_HEADERS[cmd]) - 1
    if len(args) != expected:
        await update.message.reply_text(f"Ошибка! Для /{cmd} нужно {expected} параметров через пробел.")
        return

    try:
        append_row_smart(cmd, args)
        await update.message.reply_text(f"? {cmd.upper()}: данные внесены.")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("? Ошибка при записи в таблицу.")

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен. Жду команды: /mnp, /b2b, /phone, /migr, /new, /22")

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден!")
        return
    
    app = Application.builder().token(token).build()
    
    for cmd in SHEET_HEADERS.keys():
        app.add_handler(CommandHandler(cmd, cmd_handler))
    
    app.add_handler(CommandHandler("start", cmd_start))
    
    logger.info("Бот запущен...")
    app.run_polling(poll_interval=1.0, timeout=30)

if __name__ == "__main__":
    main()