import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
from dotenv import load_dotenv
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv()
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# Настройка авторизации для Google Sheets
def setup_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).sheet1
        logger.info("Google Sheets успешно настроен")
        return sheet
    except Exception as e:
        logger.error(f"Ошибка при настройке Google Sheets: {e}")
        raise

# Функция для добавления новой строки в Google Sheet
def add_to_sheet(sheet, date, code, product_name, actual_stock, egais_stock):
    try:
        # Формируем данные для новой строки
        discrepancy = actual_stock - egais_stock
        row = [date, code, product_name, actual_stock, egais_stock, discrepancy]
        
        # Добавляем строку в Google Sheet
        sheet.append_row(row)
        logger.info(f"Добавлена новая строка в Google Sheets: {code} - {product_name}, Факт: {actual_stock}, ЕГАИС: {egais_stock}")
    except Exception as e:
        logger.error(f"Ошибка при добавлении строки в Google Sheets: {e}")
        raise