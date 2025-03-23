import os
import datetime
import logging
import json
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from google_sheets import setup_google_sheets, add_to_sheet

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
load_dotenv()
DOWNLOAD_DIR = "C:\\Users\\Максим\\Documents\\Остатки ЕГАИС"
NOTIFY_CHAT_ID = "-1002260669289"  # ID группы для уведомлений
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # ID администратора из .env
PRODUCTS_FILE = "products.json"  # Файл для хранения списка продуктов

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

sheet = setup_google_sheets()

# Функция для загрузки продуктов из файла
def load_products():
    try:
        if os.path.exists(PRODUCTS_FILE):
            with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
                products = json.load(f)
                logger.info(f"Продукты загружены из {PRODUCTS_FILE}")
                return products
        else:
            logger.info(f"Файл {PRODUCTS_FILE} не найден, создаётся пустой список")
            save_products([])
            return []
    except Exception as e:
        logger.error(f"Ошибка при загрузке продуктов: {e}")
        save_products([])
        return []

# Функция для сохранения продуктов в файл
def save_products(products):
    try:
        with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=4)
        logger.info(f"Продукты сохранены в {PRODUCTS_FILE}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении продуктов: {e}")

# Загружаем продукты при запуске
PRODUCTS = load_products()

# Проверка, является ли пользователь администратором
def is_admin(update: Update):
    logger.info(f"Проверка админа: user_id={update.effective_user.id}, ADMIN_ID={ADMIN_ID}")
    return update.effective_user.id == ADMIN_ID

# Панель администратора
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"Запуск админ-панели для user_id={update.effective_user.id}")
        if not is_admin(update):
            logger.info("Пользователь не админ")
            await context.bot.send_message(update.effective_chat.id, "Эта функция доступна только администратору.")
            return
        
        logger.info("Создание клавиатуры")
        keyboard = [
            [InlineKeyboardButton("Добавить товар", callback_data='admin_add')],
            [InlineKeyboardButton("Удалить товар", callback_data='admin_remove')],
            [InlineKeyboardButton("Список товаров", callback_data='admin_list')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        logger.info(f"Отправка сообщения в чат {update.effective_chat.id}")
        await context.bot.send_message(update.effective_chat.id, "Панель администратора:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка в admin_panel: {e}", exc_info=True)
        raise

# Показать панель администратора после действия
async def show_admin_panel(chat_id, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            [InlineKeyboardButton("Добавить товар", callback_data='admin_add')],
            [InlineKeyboardButton("Удалить товар", callback_data='admin_remove')],
            [InlineKeyboardButton("Список товаров", callback_data='admin_list')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id, "Панель администратора:", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка в show_admin_panel: {e}")

# Команда добавления товара (через кнопки)
async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        context.user_data['admin_state'] = 'add_code'
        await query.message.reply_text("Введите код нового товара (например, 999):")
    except Exception as e:
        logger.error(f"Ошибка в handle_add_product: {e}")

# Команда удаления товара (через кнопки)
async def handle_remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        context.user_data['admin_state'] = 'remove_code'
        await query.message.reply_text("Введите код товара для удаления (например, 109):")
    except Exception as e:
        logger.error(f"Ошибка в handle_remove_product: {e}")

# Команда списка товаров
async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not PRODUCTS:
            await context.bot.send_message(update.effective_chat.id, "Список товаров пуст.")
            return
        
        products_text = "Текущий список товаров:\n" + "\n".join([f"{p['short_name']} ({p['code']})" for p in PRODUCTS])
        await context.bot.send_message(update.effective_chat.id, products_text)
    except Exception as e:
        logger.error(f"Ошибка в list_products: {e}")

# Обработка ввода администратора
async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update) or 'admin_state' not in context.user_data:
        return
    
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    state = context.user_data['admin_state']

    try:
        if state == 'add_code':
            context.user_data['new_product_code'] = text
            context.user_data['admin_state'] = 'add_name'
            await update.message.reply_text("Введите название товара (например, Апельсин):")
        
        elif state == 'add_name':
            code = context.user_data['new_product_code']
            short_name = text
            if any(p["code"] == code for p in PRODUCTS):
                await update.message.reply_text(f"Товар с кодом {code} уже существует.")
            else:
                PRODUCTS.append({"code": code, "short_name": short_name})
                save_products(PRODUCTS)
                await update.message.reply_text(f"Товар добавлен: {short_name} ({code})")
                logger.info(f"Добавлен товар: {code} - {short_name}")
            context.user_data.pop('admin_state', None)
            context.user_data.pop('new_product_code', None)
            await show_admin_panel(chat_id, context)
        
        elif state == 'remove_code':
            code = text
            initial_len = len(PRODUCTS)
            PRODUCTS[:] = [p for p in PRODUCTS if p["code"] != code]
            if len(PRODUCTS) < initial_len:
                save_products(PRODUCTS)
                await update.message.reply_text(f"Товар с кодом {code} удалён.")
                logger.info(f"Удалён товар с кодом: {code}")
            else:
                await update.message.reply_text(f"Товар с кодом {code} не найден.")
            context.user_data.pop('admin_state', None)
            await show_admin_panel(chat_id, context)
    
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
        logger.error(f"Ошибка при обработке ввода администратора: {e}")
        context.user_data.pop('admin_state', None)
        await show_admin_panel(chat_id, context)

def process_stock_file():
    try:
        files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.xlsx') and not f.startswith('~$')]
        if not files:
            raise FileNotFoundError("Файл остатков (.xlsx) не найден в папке.")
        
        latest_file = max([os.path.join(DOWNLOAD_DIR, f) for f in files], key=os.path.getmtime)
        file_time = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file))
        current_time = datetime.datetime.now()
        time_difference = (current_time - file_time).total_seconds() / 3600
        
        if time_difference > 24:
            raise ValueError(f"Файл остатков устарел (дата: {file_time.strftime('%Y-%m-%d %H:%M')}). Загрузите актуальный файл.")
        
        if len(files) > 1:
            logger.warning(f"Найдено несколько файлов: {files}. Используется: {latest_file}")
        
        df = pd.read_excel(latest_file, header=3)
        if "Код товара" not in df.columns or "Наименование карточки товара" not in df.columns or "Количество (1 регистр)" not in df.columns:
            raise KeyError("В файле отсутствуют необходимые столбцы.")
        
        stock_data = {}
        for _, row in df.iterrows():
            code = str(row["Код товара"])
            name = row["Наименование карточки товара"]
            quantity = row["Количество (1 регистр)"]
            if code in stock_data:
                stock_data[code]["quantity"] += quantity
            else:
                stock_data[code] = {"name": name, "quantity": quantity}
        return stock_data
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}")
        return None

def update_sheet_row(sheet, date, code, product_name, actual_stock, egais_stock):
    try:
        cell_list = sheet.findall(code)
        for cell in cell_list:
            row = sheet.row_values(cell.row)
            if row[0] == date and row[1] == code:
                sheet.update(range_name=f'A{cell.row}:F{cell.row}', values=[[date, code, product_name, actual_stock, egais_stock, actual_stock - egais_stock]])
                logger.info(f"Обновлена строка в Google Sheets: {code} на {actual_stock}")
                return
        add_to_sheet(sheet, date, code, product_name, actual_stock, egais_stock)
    except Exception as e:
        logger.error(f"Ошибка при обновлении строки: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    context.user_data['actual_stocks'] = {}
    context.user_data['product_index'] = 0
    context.user_data['state'] = 'ready_check'

    files = [f for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.xlsx') and not f.startswith('~$')]
    if not files:
        await update.message.reply_text("Привет! Тест3 Файл остатков не найден в папке. Добавьте его в C:\\Users\\Максим\\Documents\\Остатки ЕГАИС и попробуйте снова.")
        return
    
    latest_file = max([os.path.join(DOWNLOAD_DIR, f) for f in files], key=os.path.getmtime)
    file_time = datetime.datetime.fromtimestamp(os.path.getmtime(latest_file))
    current_time = datetime.datetime.now()
    time_difference = (current_time - file_time).total_seconds() / 3600
    
    if time_difference > 24:
        await update.message.reply_text(f"Файл остатков устарел (дата: {file_time.strftime('%Y-%m-%d %H:%M')}). Пожалуйста, загрузите актуальный файл в C:\\Users\\Максим\\Documents\\Остатки ЕГАИС и попробуйте снова.")
        return
    
    intro_text = (
        "Привет! Я бот для сверки остатков.\n"
        "Я буду запрашивать фактические остатки для каждого товара по очереди.\n"
        "Отвечайте числом остатка для каждого товара.\n"
        f"Используется файл: {os.path.basename(latest_file)} (дата: {file_time.strftime('%Y-%m-%d %H:%M')})"
    )
    if len(files) > 1:
        intro_text += f"\nВ папке несколько файлов. Используется самый свежий."
    
    await update.message.reply_text(intro_text)
    
    keyboard = [
        [InlineKeyboardButton("Да", callback_data='ready_yes'), InlineKeyboardButton("Нет", callback_data='ready_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(update.effective_chat.id, "Готовы ли для подсчета фактических остатков?", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📋 **Справка по боту:**\n"
        "- /start — Начать процесс сверки остатков.\n"
        "- /history — Показать историю остатков по товару (бот покажет список товаров и запросит код, затем выбор периода).\n"
        "- Используйте кнопки для навигации по процессу.\n"
        "Введите остатки числом для каждого товара.\n\n"
    )
    
    if is_admin(update):
        help_text += (
            "🔑 **Администраторские функции:**\n"
            "Вы можете открыть панель администратора, нажав кнопку ниже или введя любой текст для активации.\n"
        )
        keyboard = [[InlineKeyboardButton("Открыть панель администратора", callback_data='admin_open')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        reply_markup = None
    
    await context.bot.send_message(update.effective_chat.id, help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.info(f"Запуск команды /history для user_id={update.effective_user.id}")
        if not PRODUCTS:
            logger.info("Список товаров пуст")
            await context.bot.send_message(update.effective_chat.id, "Список товаров пуст. Добавьте товары через админ-панель.")
            return
        
        # Формируем список товаров
        products_text = "Список товаров:\n" + "\n".join([f"{p['short_name']} ({p['code']})" for p in PRODUCTS])
        logger.info(f"Отправка списка товаров: {products_text}")
        await context.bot.send_message(update.effective_chat.id, products_text)
        
        # Запрашиваем код товара и переходим в состояние выбора
        logger.info("Запрос кода товара и установка состояния history_select")
        await context.bot.send_message(update.effective_chat.id, "Введите код товара, чтобы посмотреть историю (например, 999):")
        context.user_data['state'] = 'history_select'
        
    except Exception as e:
        logger.error(f"Ошибка в history_command: {e}", exc_info=True)
        await context.bot.send_message(update.effective_chat.id, f"Ошибка: {e}")

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != 'private':
        return
    
    if 'admin_state' in context.user_data:
        await handle_admin_input(update, context)
        return
    
    state = context.user_data.get('state', 'input')
    logger.info(f"Текущее состояние: {state}, текст ввода: {update.message.text.strip()}")
    
    try:
        if state == 'history_select':
            code = update.message.text.strip()
            logger.info(f"Введён код товара: {code}")
            # Проверяем, есть ли такой код в списке товаров
            if not any(p['code'] == code for p in PRODUCTS):
                logger.info(f"Товар с кодом {code} не найден")
                await context.bot.send_message(update.effective_chat.id, f"Товар с кодом {code} не найден. Попробуйте снова:")
                return
            
            # Сохраняем код товара
            context.user_data['history_code'] = code
            logger.info(f"Сохранён код товара: {code}")
            
            # Показываем кнопки для выбора периода
            keyboard = [
                [InlineKeyboardButton("5 дней", callback_data='period_5'),
                 InlineKeyboardButton("10 дней", callback_data='period_10')],
                [InlineKeyboardButton("20 дней", callback_data='period_20'),
                 InlineKeyboardButton("30 дней", callback_data='period_30')],
                [InlineKeyboardButton("Завершить", callback_data='history_done')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            logger.info("Создание и отправка клавиатуры для выбора периода")
            await context.bot.send_message(update.effective_chat.id, "Выберите период для истории:", reply_markup=reply_markup)
            context.user_data['state'] = 'history_period'
            logger.info("Установлено состояние history_period")
        
        elif state == 'input':
            product_index = context.user_data['product_index']
            stock = int(update.message.text.strip())
            product = PRODUCTS[product_index]
            await update.message.reply_text(f"Добавлено: {product['short_name']} ({product['code']}) = {stock}")
            context.user_data['actual_stocks'][product['code']] = stock
            context.user_data['product_index'] += 1
            
            if context.user_data['product_index'] < len(PRODUCTS):
                next_product = PRODUCTS[context.user_data['product_index']]
                await context.bot.send_message(update.effective_chat.id, f"Введите остаток для {next_product['short_name']} ({next_product['code']}):")
            else:
                keyboard = [
                    [InlineKeyboardButton("Да", callback_data='check_yes'), InlineKeyboardButton("Нет", callback_data='check_no')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(update.effective_chat.id, "Все фактические остатки введены. Провести сверку?", reply_markup=reply_markup)
                context.user_data['state'] = 'check'
        
        elif state == 'edit_value':
            stock = int(update.message.text.strip())
            code = context.user_data['edit_code']
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            system_stocks = context.user_data['system_stocks']
            system_data = system_stocks.get(code, {"name": "", "quantity": 0})
            name = system_data["name"]
            system_stock = system_data["quantity"]
            context.user_data['actual_stocks'][code] = stock
            update_sheet_row(sheet, today, code, name, stock, system_stock)
            await update.message.reply_text(f"Обновлено: {name} ({code}) = {stock}")
            
            discrepancies = [
                f"{system_stocks[c]['name']} ({c}): Факт = {context.user_data['actual_stocks'][c]}, ЕГАИС = {system_stocks[c]['quantity']}, Расхождение = {context.user_data['actual_stocks'][c] - system_stocks[c]['quantity']}"
                for c in context.user_data['actual_stocks'].keys() & system_stocks.keys()
                if context.user_data['actual_stocks'][c] != system_stocks[c]['quantity']
            ]
            context.user_data['discrepancies'] = discrepancies
            if discrepancies:
                keyboard = [
                    [InlineKeyboardButton("Да", callback_data='edit_yes'), InlineKeyboardButton("Нет", callback_data='edit_no')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(update.effective_chat.id, "Расхождения остались:\n" + "\n".join(discrepancies) + "\nИсправить ещё один товар?", reply_markup=reply_markup)
                context.user_data['state'] = 'edit'
            else:
                keyboard = [
                    [InlineKeyboardButton("Да", callback_data='send_yes'), InlineKeyboardButton("Нет", callback_data='send_no')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(update.effective_chat.id, "Отправить остатки в группу?", reply_markup=reply_markup)
                context.user_data['state'] = 'send'
        
        elif state == 'edit':
            response = update.message.text.strip().lower()
            if any(d.split('(')[1].startswith(response + ')') for d in context.user_data['discrepancies']):
                context.user_data['edit_code'] = response
                context.user_data['state'] = 'edit_value'
                await context.bot.send_message(update.effective_chat.id, f"Введите новый остаток для товара с кодом {response}:")
            else:
                await context.bot.send_message(update.effective_chat.id, "Неверный код. Введите код из списка расхождений:")
    
    except ValueError:
        if state == 'input':
            product = PRODUCTS[context.user_data['product_index']]
            await context.bot.send_message(update.effective_chat.id, f"Пожалуйста, введите число для {product['short_name']} ({product['code']}):")
        elif state == 'edit_value':
            await context.bot.send_message(update.effective_chat.id, "Пожалуйста, введите число для нового остатка:")
        elif state == 'history_select':
            await context.bot.send_message(update.effective_chat.id, "Пожалуйста, введите код товара (например, 999):")
    except Exception as e:
        logger.error(f"Ошибка ввода: {e}", exc_info=True)
        await context.bot.send_message(update.effective_chat.id, f"Ошибка: {e}. Попробуйте снова.")

async def perform_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    wait_msg = await context.bot.send_message(chat_id, "Идёт сверка остатков, пожалуйста, подождите...")
    
    try:
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        system_stocks = process_stock_file()
        if not system_stocks:
            await context.bot.send_message(chat_id, "Ошибка обработки файла остатков. Проверьте файл и попробуйте снова.")
            return
        
        processed = 0
        discrepancies = []
        for code in set(context.user_data['actual_stocks'].keys()) | set(system_stocks.keys()):
            actual_stock = context.user_data['actual_stocks'].get(code, 0)
            system_data = system_stocks.get(code, {"name": "", "quantity": 0})
            name = system_data["name"]
            system_stock = system_data["quantity"]
            add_to_sheet(sheet, today, code, name, actual_stock, system_stock)
            processed += 1
            discrepancy = actual_stock - system_stock
            if discrepancy != 0:
                discrepancies.append(f"{name} ({code}): Факт = {actual_stock}, ЕГАИС = {system_stock}, Расхождение = {discrepancy}")
        
        context.user_data['system_stocks'] = system_stocks
        context.user_data['discrepancies'] = discrepancies
        message_text = f"Сверка завершена. Обработано: {processed} товаров"
        if discrepancies:
            message_text += "\nРасхождения:\n" + "\n".join(discrepancies) + "\nЕсть расхождения. Перепроверить позиции?"
            keyboard = [
                [InlineKeyboardButton("Да", callback_data='review_yes'), InlineKeyboardButton("Нет", callback_data='review_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.user_data['state'] = 'review'
            await context.bot.send_message(chat_id, message_text, reply_markup=reply_markup)
        else:
            keyboard = [
                [InlineKeyboardButton("Да", callback_data='send_yes'), InlineKeyboardButton("Нет", callback_data='send_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, "Отправить остатки в группу?", reply_markup=reply_markup)
            context.user_data['state'] = 'send'
    except Exception as e:
        logger.error(f"Ошибка при сверке: {e}", exc_info=True)
        await context.bot.send_message(chat_id, f"Ошибка при сверке: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        chat_id = query.message.chat_id
        logger.info(f"Получен callback: data={query.data}, user_id={update.effective_user.id}, chat_id={chat_id}")
        
        # Обработка query.answer отдельно
        try:
            await query.answer()
            logger.info("query.answer() успешно выполнен")
        except Exception as e:
            logger.error(f"Ошибка в query.answer(): {e}", exc_info=True)
            # Продолжаем выполнение, даже если query.answer() не сработал
        
        data = query.data
        logger.info(f"Данные callback: {data}")
        
        # Обработка выбора периода для истории
        if data.startswith('period_'):
            days = int(data.split('_')[1])  # Извлекаем количество дней (5, 10, 20, 30)
            code = context.user_data.get('history_code')
            logger.info(f"Выбран период: {days} дней, код товара: {code}")
            
            if not code:
                logger.error("Код товара отсутствует в context.user_data['history_code']")
                await context.bot.send_message(chat_id, "Произошла ошибка: код товара не сохранён. Пожалуйста, начните заново с команды /history.")
                context.user_data.pop('state', None)
                context.user_data.pop('history_code', None)
                return
            
            # Вычисляем дату начала периода
            today = datetime.datetime.now()
            start_date = today - datetime.timedelta(days=days)
            
            # Получаем историю из Google Sheets
            all_data = sheet.get_all_values()
            history = []
            
            for row in all_data:
                if len(row) >= 2 and row[1] == code:  # Проверяем, что строка содержит код
                    try:
                        row_date = datetime.datetime.strptime(row[0], '%Y-%m-%d')
                        if start_date <= row_date <= today:  # Фильтруем по дате
                            date = row[0]
                            actual_stock = float(row[3]) if row[3] else 0  # Фактический остаток
                            egais_stock = float(row[4]) if row[4] else 0   # Остаток ЕГАИС
                            discrepancy = actual_stock - egais_stock
                            history.append(f"{date}: Факт = {actual_stock}, ЕГАИС = {egais_stock}, Расхождение = {discrepancy}")
                    except ValueError:
                        logger.warning(f"Некорректный формат даты в строке: {row[0]}")
                        continue
            
            if not history:
                logger.info(f"История для товара {code} за {days} дней не найдена")
                await context.bot.send_message(chat_id, f"История для товара с кодом {code} за последние {days} дней не найдена.")
            else:
                logger.info(f"Отправка истории для товара {code} за {days} дней")
                history_text = f"История для товара с кодом {code} (последние {days} дней):\n" + "\n".join(history)
                await context.bot.send_message(chat_id, history_text)
            
            # Повторно показываем кнопки для выбора периода
            keyboard = [
                [InlineKeyboardButton("5 дней", callback_data='period_5'),
                 InlineKeyboardButton("10 дней", callback_data='period_10')],
                [InlineKeyboardButton("20 дней", callback_data='period_20'),
                 InlineKeyboardButton("30 дней", callback_data='period_30')],
                [InlineKeyboardButton("Завершить", callback_data='history_done')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, "Выберите другой период или завершите:", reply_markup=reply_markup)
            return
        
        # Обработка завершения процесса истории
        if data == 'history_done':
            logger.info("Пользователь завершил просмотр истории")
            await context.bot.send_message(chat_id, "Просмотр истории завершён.")
            context.user_data.pop('state', None)
            context.user_data.pop('history_code', None)
            return
        
        # Сначала проверяем admin_open
        if data == 'admin_open' and is_admin(update):
            logger.info(f"Перед вызовом admin_panel для user_id={update.effective_user.id}")
            await admin_panel(update, context)
            logger.info("Админ-панель должна быть отправлена")
            return
        
        # Затем проверяем admin_ (add, remove, list)
        if data.startswith('admin_'):
            logger.info("Обработка admin_ callback")
            if not is_admin(update):
                await query.message.reply_text("Эта функция доступна только администратору.")
                return
            
            if data == 'admin_add':
                await handle_add_product(update, context)
            elif data == 'admin_remove':
                await handle_remove_product(update, context)
            elif data == 'admin_list':
                await list_products(update, context)
                await show_admin_panel(chat_id, context)
            return
        
        if query.message.chat.type != 'private':
            logger.info("Сообщение не в приватном чате")
            return
        
        if data == 'ready_yes':
            context.user_data['state'] = 'input'
            if not PRODUCTS:
                await context.bot.send_message(chat_id, "Список товаров пуст. Обратитесь к администратору для добавления товаров.")
                return
            product = PRODUCTS[0]
            await context.bot.send_message(chat_id, f"Введите остаток для {product['short_name']} ({product['code']}):")
        elif data == 'ready_no':
            await context.bot.send_message(chat_id, "Хорошо, вернитесь когда будете готовы!")
        elif data == 'check_yes':
            await perform_check(update, context)
        elif data == 'check_no':
            context.user_data['state'] = 'confirm_cancel'
            keyboard = [
                [InlineKeyboardButton("Да", callback_data='cancel_yes'), InlineKeyboardButton("Нет", callback_data='cancel_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, "Вы уверены, что хотите прервать процесс сверки?", reply_markup=reply_markup)
        elif data == 'cancel_yes':
            await context.bot.send_message(chat_id, "Сверка отменена.")
        elif data == 'cancel_no':
            context.user_data['state'] = 'check'
            keyboard = [
                [InlineKeyboardButton("Да", callback_data='check_yes'), InlineKeyboardButton("Нет", callback_data='check_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, "Все фактические остатки введены. Провести сверку?", reply_markup=reply_markup)
        elif data == 'review_yes':
            context.user_data['state'] = 'edit'
            discrepancies = context.user_data['discrepancies']
            await context.bot.send_message(chat_id, "Расхождения:\n" + "\n".join(discrepancies) + "\nИсправить данные для какого товара? Введите код:")
        elif data == 'review_no':
            discrepancies = context.user_data['discrepancies']
            keyboard = [
                [InlineKeyboardButton("Да", callback_data='send_yes'), InlineKeyboardButton("Нет", callback_data='send_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, "Отправить остатки в группу?", reply_markup=reply_markup)
            context.user_data['state'] = 'send'
        elif data == 'edit_yes':
            discrepancies = context.user_data['discrepancies']
            await context.bot.send_message(chat_id, "Расхождения:\n" + "\n".join(discrepancies) + "\nИсправить данные для какого товара? Введите код:")
        elif data == 'edit_no':
            discrepancies = context.user_data['discrepancies']
            keyboard = [
                [InlineKeyboardButton("Да", callback_data='send_yes'), InlineKeyboardButton("Нет", callback_data='send_no')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, "Отправить остатки в группу?", reply_markup=reply_markup)
            context.user_data['state'] = 'send'
        elif data == 'send_yes':
            discrepancies = context.user_data.get('discrepancies', [])
            message_text = "Результаты сверки:\nОбработано товаров: {}\n".format(len(context.user_data['actual_stocks']))
            if discrepancies:
                message_text += "Расхождения:\n" + "\n".join(discrepancies)
            else:
                message_text += "Расхождений нет."
            await context.bot.send_message(NOTIFY_CHAT_ID, message_text)
            await context.bot.send_message(chat_id, "Остатки отправлены в группу.")
        elif data == 'send_no':
            await context.bot.send_message(chat_id, "Остатки не отправлены в группу.")
    except Exception as e:
        logger.error(f"Ошибка в button_handler: {e}", exc_info=True)

def main():
    application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    
    # Настраиваем команды для меню Telegram
    commands = [
        BotCommand("start", "Начать сверку остатков"),
        BotCommand("help", "Показать справку"),
        BotCommand("history", "Показать историю остатков по товару")
    ]
    application.bot.set_my_commands(commands)
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()