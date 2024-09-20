from aiogram.filters import BaseFilter
from aiogram import types


class TextAndFilter(BaseFilter):
    def __init__(self, values):
        self.values = values

    async def __call__(self, message: types.Message):
        return message.text in self.values
