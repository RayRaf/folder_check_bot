import telebot
import os
import time
import schedule
from collections import defaultdict
from threading import Thread
import shelve


API_TOKEN = os.environ.get('TELEGRAM_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# Словарь для хранения информации о чатах и их папках
user_dirs = {}

# Функция для загрузки данных из базы данных
def load_data():
    global user_dirs
    with shelve.open('user_dirs.db') as db:
        user_dirs = db.get('user_dirs', {})

# Функция для сохранения данных в базу данных
def save_data():
    with shelve.open('user_dirs.db') as db:
        db['user_dirs'] = user_dirs

# Функция для проверки изменений в папках
def check_for_changes():
    changes_detected = False
    for user_id, dirs in user_dirs.items():
        for dir_path, prev_files in dirs.items():
            if os.path.exists(dir_path):
                current_files = set(os.listdir(dir_path))
                prev_files_set = set(prev_files)
                if current_files != prev_files_set:
                    new_files = current_files - prev_files_set
                    if new_files:
                        bot.send_message(user_id, f'Новые файлы или папки в {dir_path}: {", ".join(new_files)}')
                        changes_detected = True
                    user_dirs[user_id][dir_path] = list(current_files)
    if changes_detected:
        save_data()

# Запуск проверки изменений каждые 5 минут
def schedule_checks():
    schedule.every(5).minutes.do(check_for_changes)
    while True:
        schedule.run_pending()
        time.sleep(1)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я бот для мониторинга папок. Используйте /add dir для добавления папки и /mydirs для просмотра ваших папок.")

# Обработчик команды /add dir
@bot.message_handler(commands=['add'])
def add_directory(message):
    try:
        dir_path = message.text.split(' ', 1)[1]
        if os.path.isdir(dir_path):
            if message.chat.id not in user_dirs:
                user_dirs[message.chat.id] = {}
            if dir_path not in user_dirs[message.chat.id]:
                user_dirs[message.chat.id][dir_path] = list(os.listdir(dir_path))
                bot.reply_to(message, f'Папка {dir_path} добавлена в список наблюдения.')
                save_data()
            else:
                bot.reply_to(message, f'Папка {dir_path} уже находится в списке наблюдения.')
        else:
            bot.reply_to(message, 'Указанный путь не является директорией.')
    except IndexError:
        bot.reply_to(message, 'Пожалуйста, укажите путь к директории после команды /add.')

# Обработчик команды /mydirs
@bot.message_handler(commands=['mydirs'])
def list_directories(message):
    dirs = user_dirs.get(message.chat.id, {})
    if dirs:
        bot.reply_to(message, 'Ваши наблюдаемые папки:\n' + '\n'.join(dirs.keys()))
    else:
        bot.reply_to(message, 'У вас нет наблюдаемых папок.')

if __name__ == '__main__':
    load_data()
    Thread(target=schedule_checks).start()
    bot.polling(none_stop=True)
