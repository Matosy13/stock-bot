import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging

# Настройка доступа к Google Таблицам
def setup_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("Bar Stock by Flavor (Rows)").sheet1  # Название вашей таблицы
    return sheet

# Добавление данных в таблицу с обработкой ошибок и логированием
def add_to_sheet(sheet, date, code, product_name, actual_stock, egais_stock):
    discrepancy = actual_stock - egais_stock
    try:
        sheet.append_row([date, code, product_name, actual_stock, egais_stock, discrepancy])
        logging.info(f"Данные добавлены: {date}, {code}, {product_name}, {actual_stock}, {egais_stock}, {discrepancy}")
    except Exception as e:
        logging.error(f"Ошибка при добавлении данных в таблицу: {e}")