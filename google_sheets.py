import os
import json
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
import gspread

# Загружаем переменные окружения из .env
load_dotenv()

def setup_google_sheets():
    # Определяем scope для Google Sheets API
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    with open('credentials.json', 'r') as file:
        credentials_dict = json.load(file)

    # Создаём учётные данные
    creds = Credentials.from_service_account_info(
        credentials_dict,
        scopes=scope
    )

    # Авторизуемся в Google Sheets
    client = gspread.authorize(creds)

    # Открываем таблицу по её ключу
    return client.open_by_key('1ETzy6vwdIBqXRohHSPT7XZ1joFyMpgxbtmpI16j_tnw').sheet1

def add_to_sheet(sheet, data):
    """
    Добавляет данные в Google Sheets.
    sheet: объект листа (возвращается из setup_google_sheets)
    data: список значений для добавления (например, [дата, продукт, количество])
    """
    # Добавляем новую строку в таблицу
    sheet.append_row(data)