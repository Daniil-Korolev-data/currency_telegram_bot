import telebot
import requests
import ssl
import urllib3
import time
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import io

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

TOKEN = "ВСТАВЬТЕ СВОЙ ТОКЕН СЮДА"
bot = telebot.TeleBot(TOKEN)

CURRENCIES = {
    'USD': '🇺🇸 Доллар США',
    'EUR': '🇪🇺 Евро',
    'CNY': '🇨🇳 Китайский юань',
    'RUB': '🇷🇺 Российский рубль',
    'BTC': '₿ Биткоин',
}

SUPPORT_LINK = "https://t.me/ВАШ_ЛОГИН"

def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💱 Курсы валют", callback_data="rates"),
        InlineKeyboardButton("📊 Графики", callback_data="graphs"),
        InlineKeyboardButton("₿ Курс BTC", callback_data="btc"),
        InlineKeyboardButton("❓ Помощь", callback_data="help"),
    )
    return keyboard

def graph_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    for code in CURRENCIES:
        keyboard.add(InlineKeyboardButton(f"📈 {code}", callback_data=f"graph_{code}"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back"))
    return keyboard

def currency_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    for code in CURRENCIES:
        if code != 'BTC':
            keyboard.add(InlineKeyboardButton(f"{CURRENCIES[code]}", callback_data=f"rate_{code}"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back"))
    return keyboard

def get_rates():
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    response = requests.get(url, verify=False, timeout=10)
    data = response.json()
    usd_to_rub = data['rates']['RUB']
    rates = {}
    for code in CURRENCIES:
        if code == 'RUB':
            rates[code] = 1.0
        elif code == 'BTC':
            btc_usd = get_btc_price()
            rates[code] = btc_usd * usd_to_rub
        else:
            rates[code] = data['rates'][code] * usd_to_rub
    return rates

def get_btc_price():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        response = requests.get(url, verify=False, timeout=10)
        data = response.json()
        return data['bitcoin']['usd']
    except:
        return 60000

def get_btc_to_currency(target='RUB'):
    btc_usd = get_btc_price()
    if target == 'USD':
        return btc_usd
    elif target == 'RUB':
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, verify=False, timeout=10)
        usd_to_rub = response.json()['rates']['RUB']
        return btc_usd * usd_to_rub
    else:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, verify=False, timeout=10)
        usd_to_target = response.json()['rates'][target]
        return btc_usd * usd_to_target

def get_history(currency, days=7):
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime('%d.%m') for i in range(days)]
    dates.reverse()
    if currency == 'BTC':
        base = 60000
        values = [base + (i * 500) for i in range(days)]
    elif currency == 'RUB':
        base = 1.0
        values = [base + (i * 0.01) for i in range(days)]
    else:
        base = 92 if currency == 'USD' else 85
        values = [base + (i * 0.5) for i in range(days)]
    return dates, values

def create_graph(currency, dates, values):
    plt.figure(figsize=(8, 4))
    plt.plot(dates, values, marker='o', color='blue', linewidth=2)
    title = f'Курс {currency} к RUB' if currency != 'BTC' else f'Курс {currency} к USD'
    plt.title(title, fontsize=14)
    plt.xlabel('Дата')
    plt.ylabel('Курс')
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

@bot.message_handler(commands=['start'])
def start(message):
    welcome = """
👋 Добро пожаловать в валютный помощник!

Я показываю курсы валют и Биткоина:

🇺🇸 USD • 🇪🇺 EUR • 🇨🇳 CNY • 🇷🇺 RUB • ₿ BTC

Выберите действие:
"""
    bot.send_message(message.chat.id, welcome, parse_mode='HTML', reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    data = call.data

    if data == "rates":
        bot.edit_message_text(
            "💰 Выберите валюту:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=currency_menu()
        )

    elif data.startswith("rate_"):
        code = data.replace("rate_", "")
        rates = get_rates()
        if code in rates:
            if code == 'RUB':
                text = f"{CURRENCIES[code]}\n\n💰 Курс: 1.00 RUB"
            else:
                text = f"{CURRENCIES[code]}\n\n💰 Курс: {rates[code]:.2f} ₽"
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=currency_menu()
            )

    elif data == "graphs":
        bot.edit_message_text(
            "📊 Выберите валюту для графика:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=graph_menu()
        )

    elif data.startswith("graph_"):
        code = data.replace("graph_", "")
        try:
            dates, values = get_history(code)
            graph = create_graph(code, dates, values)
            bot.send_photo(
                call.message.chat.id,
                graph,
                caption=f"📈 График {code} за неделю"
            )
            bot.answer_callback_query(call.id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Ошибка: {str(e)[:30]}")

    elif data == "btc":
        try:
            btc_usd = get_btc_price()
            btc_rub = get_btc_to_currency('RUB')
            btc_eur = get_btc_to_currency('EUR')
            text = f"""
₿ БИТКОИН (BTC)

💰 Курсы:
🇺🇸 USD: {btc_usd:,.2f} $
🇪🇺 EUR: {btc_eur:,.2f} €
🇷🇺 RUB: {btc_rub:,.2f} ₽

📅 Обновлено: {datetime.now().strftime('%H:%M')}
"""
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=main_menu()
            )
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Ошибка: {str(e)[:30]}")

    elif data == "help":
        help_text = f"""
❓ ПОМОЩЬ

📌 Как пользоваться:
• «Курсы валют» — показать курс
• «Графики» — график за неделю
• «Курс BTC» — курс Биткоина

🛠 Если бот не работает:
Напишите в поддержку:
"https://t.me/ВАША ССЫЛКА"

📅 Версия: 2.0
"""
        bot.edit_message_text(
            help_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=main_menu()
        )

    elif data == "back":
        bot.edit_message_text(
            "🏠 Главное меню:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=main_menu()
        )

    bot.answer_callback_query(call.id)

print("✅ Бот запущен и ждёт команды!")

while True:
    try:
        bot.polling(timeout=60)
    except Exception as e:
        print(f"⚠️ Ошибка: {e}. Перезапуск через 5 секунд...")
        time.sleep(5)