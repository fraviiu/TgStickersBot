import time
from random import choice
import asyncio

from aiogram import types

from models import User
import config

# тут задачи ежи
async def worker():
	while True:
		start = time.monotonic()
		User.update({User.score: User.score + 1}).execute()
		if (end := time.monotonic() - start) > config.delay: 
			end = config.delay
		await asyncio.sleep(config.delay - end)


class Markup:
	cancels = ['Отмена', 'Отменить действие', 'Отменить']

	def every_state(self, markup=None):
		if not markup:
			markup = types.ReplyKeyboardMarkup(resize_keyboard=True,
				one_time_keyboard=True)
		markup.row(choice(self.cancels))
		return markup

	def after_cancel(self):
		return types.ReplyKeyboardRemove()