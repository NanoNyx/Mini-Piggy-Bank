import telebot as tg # для роботи з Telegram API
from telebot import types #клавіатура
import threading # робота з потоками
import os # взяття інформації про середовище, робота з файловою системою
import time
import datetime # для роботи з датами та часом
import re
from collections import defaultdict # дозволяє задавати значення за замовчуванням для ключів, які ще не існують у словнику
import openpyxl #операції з файлами Excel

bot = tg.TeleBot(os.getenv("API_TOKEN"))


def bot_check():
  return bot.get_me()


def bot_runner():
  bot.infinity_polling(none_stop=True)


t = threading.Thread(target=bot_runner)
t.start()

# Словник для зберігання даних користувача
user_data = {}


# Функція для перевірки коректності назви категорії
def is_valid_category_name(category_name):
  return bool(category_name)


# Функція для отримання/створення словника для визначеного користувача і категорії
def get_or_create_user_category_expenses(user_id, category):
  if user_id not in user_data:
    user_data[user_id] = {'categories': {}, 'expenses': {}}
  if category not in user_data[user_id]['expenses']:
    user_data[user_id]['expenses'][category] = []
  return user_data[user_id]['expenses'][category]


# Функція для зберігання даних в Excel
def save_data_to_excel(user_id):
  if user_id in user_data:
    workbook = openpyxl.Workbook()
    sheet = workbook.active

    # Заголовок для таблиці
    sheet.append(["Категорія", "Витрати"])

    # Додавання даних
    for category, expenses in user_data[user_id]['expenses'].items():
      for expense in expenses:
        sheet.append([category, expense])

    # Збереження до файлу
    filename = f"user_data_{user_id}.xlsx"
    workbook.save(filename)

    bot.send_document(user_id, open(filename, 'rb'))
    os.remove(filename)
  else:
    bot.send_message(user_id, "Немає даних для збереження.")


# Команда /старт
@bot.message_handler(commands=['start'])
def handle_start(message):
  user_id = message.from_user.id
  bot.send_message(
      user_id,
      "Вітаю, я Ваш фінансовий помічник. Для взаємодії натисність /start, /help або на одну з кнопок нижче."
  )
  show_commands(user_id)


# Команда /допомога
@bot.message_handler(commands=['help'])
def handle_help(message):
  user_id = message.from_user.id
  help_text = (
      "Коротка інструкція для ознайомлення:\n"
      "/start - запуск бота\n"
      "/help -  отримати довідку по використанню функціоналу бота\n"
      "Далі Ви можете користуватись кнопками з меню для виконання математичних та статистичних операцій, таких як:\n"
      "- додавання/видалення категорій,\n"
      "- фіксування й редагування бюджету/мрій,\n"
      "- відображення статистики,\n"
      "- збереження даних у зручному форматі. \n\n"
      "Пропоную відвідати мій офіціальний telegram-канал! Там багато корисної інформації для розвитку фінансової грамотності:\n https://t.me/mini_piggy_bank_channel"
  )
  bot.send_message(user_id, help_text)


# Функція для показу команд
def show_commands(user_id):
  markup = tg.types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.row("Додати категорію", "Видалити категорію")
  markup.row("Зафіксувати вклад", "Обмеження")
  markup.row("Статистика")
  markup.row("Виправити вклад", "Виправити обмеження")
  markup.add("Накопичити на мрію", "Скорегувати мрію")
  markup.row("Зберегти дані", "Очистити історію")
  bot.send_message(user_id, "Оберіть команду:", reply_markup=markup)


  # Обробник команди "Додати категорію"
@bot.message_handler(func=lambda message: message.text == "Додати категорію")
def handle_add_category(message):
  user_id = message.from_user.id

  if user_id not in user_data:
    user_data[user_id] = {'categories': {}, 'expenses': {}}

    ###
  if 'categories' not in user_data[user_id]:
    user_data[user_id]['categories'] = {}
  ###

  bot.send_message(
      user_id,
      "Введіть назву нової категорії витрат (не більше 30 символів), або напишіть 'назад' для повернення до меню."
  )
  bot.register_next_step_handler(message, process_add_category)


def process_add_category(message):
  user_id = message.from_user.id
  category_name = message.text

  if category_name.lower() == 'назад':
    show_commands(user_id)
    return

  if len(category_name) > 30:
    bot.send_message(
        user_id,
        "Назва категорії занадто довга. Введіть назву не більше ніж 30 символів."
    )
    show_commands(user_id)
    return

  if category_name in user_data[user_id]['categories']:
    bot.send_message(user_id, "У Вас вже є така категорія.")
  else:
    user_data[user_id]['categories'][category_name] = []
    bot.send_message(user_id, f"Категорію '{category_name}' додано.")
  show_commands(user_id)


# Обробник команди "Зафіксувати вклад"
@bot.message_handler(func=lambda message: message.text == "Зафіксувати вклад")
def handle_add_expense(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})

  if not user_categories:
    bot.send_message(user_id, "Спочатку додайте категорії витрат.")
    show_commands(user_id)
    return

  markup = tg.types.ReplyKeyboardMarkup(resize_keyboard=True)
  for category in user_categories:
    markup.add(category)

  markup.add("Назад")
  bot.send_message(user_id, "Оберіть категорію:", reply_markup=markup)
  bot.register_next_step_handler(message, process_choose_category)


def process_choose_category(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})
  user_expenses = user_data.get(user_id, {}).get('expenses', {})
  selected_category = message.text

  if selected_category == "Назад":
    show_commands(user_id)
    return

  if selected_category not in user_categories:
    bot.send_message(
        user_id,
        "Обраної категорії не існує. Оберіть існуючу категорію або додайте нову."
    )
    show_commands(user_id)
  else:
    if selected_category not in user_expenses:
      user_expenses[selected_category] = []
    bot.send_message(user_id, f"Введіть суму вкладу для'{selected_category}':")
    bot.register_next_step_handler(message, process_add_expense,
                                   selected_category)


def process_add_expense(message, selected_category):
  user_id = message.from_user.id
  user_expenses = user_data.get(user_id, {}).get('expenses', {})
  amount_text = message.text

  if not amount_text.isdigit():
    bot.send_message(
        user_id,
        "Вклад повинен бути додатнім числом. Оберіть категорію повторно.")
    bot.register_next_step_handler(message, process_choose_category)
    return

  amount = int(amount_text)
  user_expenses[selected_category].append(amount)
  bot.send_message(
      user_id,
      f"Вклад {amount} зафіксовано для категорії'{selected_category}'.")
  show_commands(user_id)


# Обработчик команды "Удалить категорию"
@bot.message_handler(func=lambda message: message.text == "Видалити категорію")
def handle_delete_category(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})

  if not user_categories:
    bot.send_message(user_id, "Ви не маєте категорій для видалення.")
    show_commands(user_id)
    return

  markup = tg.types.ReplyKeyboardMarkup(resize_keyboard=True)
  for category in user_categories:
    markup.add(category)

  markup.add("Назад")
  bot.send_message(user_id,
                   "Оберіть категорію для видалення:",
                   reply_markup=markup)
  bot.register_next_step_handler(message, process_delete_category)


def process_delete_category(message):
  user_id = message.from_user.id
  user_categories = user_data[user_id]['categories']
  selected_category = message.text

  if selected_category == "Назад":
    show_commands(user_id)
    return

  if selected_category not in user_categories:
    bot.send_message(
        user_id, "Обранної категорії не існує. Оберіть існуючу категорію.")
    show_commands(user_id)
    return

  if selected_category in user_data[user_id]['expenses']:
    del user_data[user_id]['expenses'][selected_category]

  del user_data[user_id]['categories'][selected_category]
  bot.send_message(user_id, f"Категорію '{selected_category}' видалено.")
  show_commands(user_id)


# Кнопка "Обмеження"
@bot.message_handler(func=lambda message: message.text == "Обмеження")
def handle_budget_limit(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})

  if not user_categories:
    bot.send_message(user_id, "Спочатку додайте категорії витрат.")
    show_commands(user_id)
    return

  markup = tg.types.ReplyKeyboardMarkup(resize_keyboard=True)
  for category in user_categories:
    markup.add(category)

  markup.add("Назад")
  bot.send_message(user_id,
                   "Оберіть категорію для встановлення обмеження:",
                   reply_markup=markup)
  bot.register_next_step_handler(message, process_set_budget_limit)


def process_set_budget_limit(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})
  selected_category = message.text

  if selected_category.lower() == 'назад':
    show_commands(user_id)
    return

  if selected_category not in user_categories:
    bot.send_message(user_id,
                     "Обранної категорії не існує. Оберіть діючу категорію.")
    show_commands(user_id)
  else:
    if user_data[user_id]['categories'][selected_category]:
      bot.send_message(
          user_id,
          f"Обмеження на місяць для категорії '{selected_category}' вже встановлено."
      )
      show_commands(user_id)
    else:
      bot.send_message(
          user_id,
          f"Встановіть обмеження для категорії '{selected_category}' на місяць (введіть число):"
      )
      bot.register_next_step_handler(message, process_set_limit_value,
                                     selected_category)


def process_set_limit_value(message, selected_category):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})
  limit_text = message.text

  if limit_text.lower() == 'назад':
    show_commands(user_id)
    return

  if not limit_text.isdigit():
    bot.send_message(
        user_id,
        "Обмеження повинно бути додатнім числом. Введіть дані коректно.")
    show_commands(user_id)
    return

  limit = int(limit_text)
  user_data[user_id]['categories'][selected_category].append(limit)
  bot.send_message(
      user_id,
      f"Обмеження для категорії '{selected_category}' встановлено на {limit} на місяць."
  )
  show_commands(user_id)


# Обробник команди "Виправити вклад"
@bot.message_handler(func=lambda message: message.text == "Виправити вклад")
def process_correct_expenses(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})
  user_expenses = user_data.get(user_id, {}).get('expenses', {})

  if not user_categories and not any(user_expenses.values()):
    bot.send_message(user_id, "Спочатку додайте категорії витрат.")
    show_commands(user_id)
    return

  markup = tg.types.ReplyKeyboardMarkup(resize_keyboard=True)
  for category in user_categories:
    markup.add(category)

  markup.add("Назад")
  bot.send_message(user_id,
                   "Оберіть категорію для редагування:",
                   reply_markup=markup)
  bot.register_next_step_handler(message, process_correct_expenses_selection)


def process_correct_expenses_selection(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})
  user_expenses = user_data.get(user_id, {}).get('expenses', {})

  selected_category = message.text
  if selected_category.lower() == 'назад':
    show_commands(user_id)
    return

  if selected_category not in user_expenses:
    bot.send_message(
        user_id,
        f"Категорія '{selected_category}' не має даних для виправлення.")
    show_commands(user_id)
    return

  user_expenses = user_data[user_id]['expenses'][selected_category]

  bot.send_message(user_id, f"Дані категорії '{selected_category}':")
  for idx, expense in enumerate(user_expenses, start=1):
    bot.send_message(user_id, f"{idx}. {expense}")

  bot.send_message(user_id, "Введіть номер(№) даних для виправлення:")
  bot.register_next_step_handler(message, process_correct_data,
                                 selected_category)


def process_correct_data(message, selected_category):
  user_id = message.from_user.id
  user_expenses = user_data.get(user_id, {}).get('expenses', {})

  try:
    expense_number = int(message.text)
  except ValueError:
    bot.send_message(user_id, "Ви обрали некоректний номер(№).")
    show_commands(user_id)
    return

  if expense_number < 1 or expense_number > len(
      user_expenses[selected_category]):
    bot.send_message(user_id, "Вы обрали некоректний номер.")
    show_commands(user_id)
    return

  # Исправление данных
  old_expense = user_expenses[selected_category][expense_number - 1]
  bot.send_message(
      user_id, f"Введіте нове додатнє число для виправлення '{old_expense}':")
  bot.register_next_step_handler(message, process_correct_expense_value,
                                 selected_category, expense_number)


def process_correct_expense_value(message, selected_category, expense_number):
  user_id = message.from_user.id
  user_expenses = user_data.get(user_id, {}).get('expenses', {})
  expense_text = message.text

  if expense_text.lower() == 'назад':
    show_commands(user_id)
    return

  try:
    new_expense = int(expense_text)
  except ValueError:
    bot.send_message(user_id,
                     "Ви ввели некоректне значення. Введіть додатнє число.")
    show_commands(user_id)
    return

  if new_expense <= 0:
    bot.send_message(
        user_id,
        "Значення повинно бути додатнім числом. Введіть додатнє число.")
    show_commands(user_id)
    return

  old_expense = user_expenses[selected_category][expense_number - 1]
  user_expenses[selected_category][expense_number - 1] = new_expense
  bot.send_message(
      user_id,
      f"Значення '{old_expense}' в категорії '{selected_category}' успішно змінено на '{new_expense}'."
  )
  show_commands(user_id)


# Обробник команди "Виправити обмеження"
@bot.message_handler(func=lambda message: message.text == "Виправити обмеження"
                     )
def process_correct_limit(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})

  if not user_categories:
    bot.send_message(user_id, "Спочатку додайте категорії витрат.")
    show_commands(user_id)
    return

  markup = tg.types.ReplyKeyboardMarkup(resize_keyboard=True)
  for category in user_categories:
    markup.add(category)

  markup.add("Назад")
  bot.send_message(
      user_id,
      "Оберіть категорію, для якої потрібно встановити обмеження:",
      reply_markup=markup)

  # Стан
  bot.register_next_step_handler(message,
                                 process_choose_category_for_limit_correction)


def process_choose_category_for_limit_correction(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})
  selected_category = message.text

  print(f"Debug: selected_category = {selected_category}")

  if selected_category.lower() == 'отмена':
    show_commands(user_id)
    return

  if selected_category not in user_categories:
    bot.send_message(user_id,
                     "Обранної категорії не існує. Оберіть діючу категорію.")
    show_commands(user_id)
    return

  if not user_data[user_id]['categories'][selected_category]:
    bot.send_message(
        user_id,
        f"Для категориї '{selected_category}' обмеження на місяць поки що не встановлено. Оберіть іншу категорію."
    )
    show_commands(user_id)
    return

  current_limit = user_data[user_id]['categories'][selected_category][0]
  bot.send_message(
      user_id,
      f"Діюче обмеження для категорії '{selected_category}' на місяць: {current_limit}. Встановіть нове обмеження:"
  )

  # Стан
  bot.register_next_step_handler(message, process_correct_limit_value,
                                 selected_category)


def process_correct_limit_value(message, selected_category):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})
  limit_text = message.text

  print(f"Debug: limit_text = {limit_text}")

  if limit_text.lower() == 'назад':
    show_commands(user_id)
    return

  if not limit_text.isdigit():
    bot.send_message(
        user_id,
        "Обмеження повинно бути додатнім числом. Введіть коректне число.")
    show_commands(user_id)
    return

  limit = int(limit_text)
  user_data[user_id]['categories'][selected_category][0] = limit
  bot.send_message(
      user_id,
      f"Обмеження для категорії '{selected_category}' успішно виправлено на {limit}."
  )
  show_commands(user_id)


# Обработчик команды "Статистика"
@bot.message_handler(func=lambda message: message.text == "Статистика")
def handle_statistics(message):
  user_id = message.from_user.id
  user_categories = user_data.get(user_id, {}).get('categories', {})
  user_expenses = user_data.get(user_id, {}).get('expenses', {})

  if not user_categories:
    bot.send_message(user_id, "Спочатку додайте категорії витрат.")
    show_commands(user_id)
    return

  today = datetime.date.today()
  current_month = today.month
  current_year = today.year

  daily_total = defaultdict(int)
  monthly_total = defaultdict(int)
  yearly_total = defaultdict(int)
  exceeded_limit_categories = []

  for category, expenses in user_expenses.items():
    if not expenses:
      daily_total[category] = monthly_total[category] = yearly_total[
          category] = 0
    else:
      for expense in expenses:
        daily_total[
            category] += expense if category in user_expenses and expense in user_expenses[
                category] else 0
        monthly_total[
            category] += expense if category in user_expenses and expense in user_expenses[
                category] else 0
        yearly_total[
            category] += expense if category in user_expenses and expense in user_expenses[
                category] else 0

      # Перевірка перевищення встановленного обмеження
      limit_list = user_data[user_id]['categories'].get(category, [])
      limit = limit_list[0] if limit_list else None

      if limit is not None and monthly_total[category] > limit:
        exceeded_limit_categories.append(category)

  # Показ результату користувачу
  result_message = "Статистика витрат:\n"
  for category in user_categories:
    result_message += f"{category}:\n"
    result_message += f"День: {daily_total[category]}\n"
    result_message += f"Місяць: {monthly_total[category]}\n"
    result_message += f"Рік: {yearly_total[category]}\n"

    # Показ обмежень
    limit_list = user_data[user_id]['categories'].get(category, [])
    limit = limit_list[0] if limit_list else None
    result_message += f"Додакові дані:\n Обмеження: {limit if limit is not None else 'відсутні'}\n\n"

  bot.send_message(user_id, result_message.strip())

  # Перевірка перевищення обмежень
  if exceeded_limit_categories:
    bot.send_message(
        user_id,
        "Ви перевищили встановлене обмеження. Щоб уникнути такого надалі, пропоную ознайомитися з порадами щодо фінансової грамотності за посиланням: https://t.me/mini_piggy_bank_channel/4"
    )

  show_commands(user_id)


# Обробник команди "Зберегти дані"
@bot.message_handler(func=lambda message: message.text == "Зберегти дані")
def handle_save_data(message):
  user_id = message.from_user.id
  save_data_to_excel(user_id)

  # Додавання збреження обмежень
  user_categories = user_data.get(user_id, {}).get('categories', {})
  result_message = "Обмеження:\n"
  for category, limit in user_categories.items():
    result_message += f"{category}: {limit[0] if limit else 'Не встановлено'}\n"

  bot.send_message(user_id, result_message.strip())
  show_commands(user_id)


# Обробник команди "Очистити історію"
@bot.message_handler(func=lambda message: message.text == "Очистити історію")
def handle_reset_data(message):
  user_id = message.from_user.id
  confirmation_markup = tg.types.ReplyKeyboardMarkup(resize_keyboard=True)
  confirmation_markup.row("Так", "Ні")
  bot.send_message(user_id,
                   "Дані будуть видалені безповоротно. Ви впевнені?",
                   reply_markup=confirmation_markup)
  bot.register_next_step_handler(message, process_reset_confirmation)


def process_reset_confirmation(message):
  user_id = message.from_user.id
  if message.text == "Так":
    if user_id in user_data:
      del user_data[user_id]
    bot.send_message(
        user_id, "Історію видалено. Для перезапуску бота натисніть /start.")
  else:
    show_commands(user_id)


# Обробник команди "Накопичити на мрію"
@bot.message_handler(func=lambda message: message.text == "Накопичити на мрію")
def handle_dream_button(message):
  user_id = message.from_user.id
  user_dreams = user_data.get(user_id, {}).get('dreams', {})

  if not user_dreams:
    bot.send_message(user_id, "Я допоможу Вам накопичити на мрію. Опишіть її:")
    bot.register_next_step_handler(message, process_dream_name)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_cancel = types.KeyboardButton("назад")
    markup.add(item_cancel)
#    bot.send_message(user_id,
#                     "Если хотите отменить действие, выберите 'Отмена'.",
#                     reply_markup=markup)
  else:
    dream_name = user_dreams.get('name', '')
    bot.send_message(user_id, f"Ваша мрія: {dream_name}")
    bot.send_message(
        user_id,
        "Відмітьте яку суму вдалось зберегти на цей раз або введіть 'назад' для повернення до меню:"
    )
    bot.register_next_step_handler(message, process_add_savings, dream_name)


# Функція для обробки вводу назви мрії
def process_dream_name(message):
  user_id = message.from_user.id
  dream_name = message.text

  if user_id not in user_data:
    user_data[user_id] = {}

  user_data[user_id]['dreams'] = {'name': dream_name, 'savings': []}

  bot.send_message(user_id, f"Ваша мрія {dream_name}")
  bot.send_message(
      user_id,
      "Відмітьте яку суму вдалось зберегти на цей раз  або введіть 'назад' для повернення до меню:"
  )
  bot.register_next_step_handler(message, process_add_savings, dream_name)


# Функція для обробки вводу числа для мрії
def process_add_savings(message, dream_name):
  user_id = message.from_user.id
  user_savings = user_data.get(user_id, {}).get('dreams',
                                                {}).get('savings', [])

  savings_text = message.text

  if savings_text.lower() == 'назад':
    show_commands(user_id)
    return

  if not savings_text.isdigit():
    bot.send_message(user_id,
                     "Число повинно бути додатнім. Введіть додатнє число.")
    bot.register_next_step_handler(message, process_add_savings, dream_name)
    return

  savings = int(savings_text)

  if savings <= 0:
    bot.send_message(user_id,
                     "Число повинно бути додатнім. Введіть додатнє число.")
    bot.register_next_step_handler(message, process_add_savings, dream_name)
    return

  user_savings.append(savings)
  total_savings = sum(user_savings)

  bot.send_message(user_id, f"Наразі Ви накопичили: {total_savings}")
  show_commands(user_id)


# Обработчик команды "Скорегувати мрію"
@bot.message_handler(func=lambda message: message.text == "Скорегувати мрію")
def handle_change_dream(message):
  user_id = message.from_user.id
  bot.send_message(user_id, "Опишіть нову мрію:")
  bot.register_next_step_handler(message, process_change_dream)


# Функція для обробки вводу нового значення для мрії
def process_change_dream(message):
  user_id = message.from_user.id
  new_dream_name = message.text

  if user_id not in user_data:
    user_data[user_id] = {}

  if 'dreams' not in user_data[user_id]:
    user_data[user_id]['dreams'] = {}

  user_data[user_id]['dreams']['savings'] = []
  user_data[user_id]['dreams']['name'] = new_dream_name

  bot.send_message(user_id, f"Ваша мрія: {new_dream_name}")
  bot.send_message(
      user_id,
      "Відмітьте яку суму вдалось зберегти на цей раз  або введіть 'назад' для повернення до меню:"
  )
  bot.register_next_step_handler(message,
                                 process_add_savings,
                                 dream_name=new_dream_name)

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  item_cancel = types.KeyboardButton("назад")
  markup.add(item_cancel)
  bot.send_message(user_id,
                   "Якщо хочете повернутись до меню, оберіть 'назад'.",
                   reply_markup=markup)


if __name__ == "__main__":
  bot.infinity_polling(none_stop=True)
