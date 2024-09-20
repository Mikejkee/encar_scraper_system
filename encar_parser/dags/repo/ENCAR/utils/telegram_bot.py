import json
import logging
import tempfile
import os

import asyncio
from aiogram import Bot, Dispatcher, types
import aiohttp
from airflow.models import Variable


logging.getLogger('asyncio').setLevel(logging.CRITICAL)
# logging.basicConfig(level=logging.INFO)

API_TOKEN = Variable.get('TELEGRAM_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
session = aiohttp.ClientSession()


async def send_data_to_group(group_chat_id: str, data_list: list, text: str):
    async with session:
        await bot.send_message(group_chat_id, f'{text}:\n' + ' '.join(map(str, data_list)))


async def send_file_to_group(group_chat_id: str, data_list: list, filename: str, min_size=64):
    async with session:
        content_json = json.dumps(data_list, indent=4)

        # Проверяем размер файла во время написания
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
            # Записываем JSON в файл
            temp_file.write(content_json)
            temp_file.flush()  # Сбрасываем буфер, чтобы записать содержимое на диск

            # Проверяем размер файла. Если он меньше min_size, добавляем пустые строки.
            current_size = os.path.getsize(temp_file.name)
            while current_size < min_size:
                temp_file.write("\n")  # Добавляем пустую строку
                temp_file.flush()  # Снова сбрасываем буфер после изменения
                current_size = os.path.getsize(temp_file.name)

            # Отправляем файл пользователю в Telegram
            await bot.send_document(group_chat_id, document=types.FSInputFile(temp_file.name,
                                                                              filename=f'{filename}.txt'))


if __name__ == '__main__':
    new_cars_urls = ['a', 'b']
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_file_to_group('-4544801957', new_cars_urls,
                                               f'Новые машины типа a'))