import logging
import os

from aiogram import Bot, Dispatcher, types, executor
from aiogram.utils.emoji import emojize, demojize
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram import types
 
from models import User
import config


logging.basicConfig(handlers=(logging.FileHandler(config.logsfile),
	logging.StreamHandler()), level=logging.INFO)



bot = Bot(token=config.token, proxy=config.proxy_url)
dp = Dispatcher(bot, storage=MemoryStorage())


class Profile(StatesGroup):
	nick = State()
	edit = State()


async def check_nick(message: types.Message):
	if User.select().where(User.nick == message.text):
		await message.answer('Пользователь с таким ником уже существует, придумайте новый')
		return True
	if len(message.text) > User.nick.max_length:
		await message.answer(f'Минимальная длинна ника {User.nick.max_length}')
		return True
	return False


@dp.message_handler(commands=['me'])
async def about_user(message: types.Message):
	try:
		user = User.get(chat_id=message.chat.id)
		markup = types.InlineKeyboardMarkup()
		edit_butt = types.InlineKeyboardButton(text='Сменить никнейм',
			callback_data='edit')
		markup.add(edit_butt)
		await message.answer(f'Ваш id: {user.chat_id}\nВаш ник: {user.nick}',
			reply_markup=markup)
	except User.DoesNotExist:
		await message.answer('Вы ещё не создали профиль, напишите свой никнейм')
		await Profile.nick.set()


@dp.message_handler(state=Profile.nick, content_types=types.ContentTypes.TEXT)
async def create_profile(message: types.Message, state: FSMContext):
	if await check_nick(message):
		return
	user = User.create(chat_id=message.chat.id, nick=emojize(message.text))
	await message.answer(f'Ваш id: {user.chat_id}\nВаш ник: {demojize(user.nick)}')
	await state.finish()


@dp.message_handler(state=Profile.edit, content_types=types.ContentTypes.TEXT)
async def edit_nick(message: types.Message, state: FSMContext):
	if await check_nick(message):
		return
	User.get(chat_id=message.chat.id).update(nick=message.text).execute()
	await state.finish()
	await message.answer('Ник изменен успешно')
	await about_user(message)


@dp.callback_query_handler(lambda call: call.data == 'edit')
async def about_edit_nick(call: types.CallbackQuery):
	await call.message.edit_text('Введите новый никнейм') 
	await Profile.edit.set()


@dp.message_handler(content_types=types.ContentTypes.STICKER)
async def n_sticker(message: types.Message):
	sticker_id = message.sticker.file_id
	await message.answer(sticker_id)
	await message.answer_sticker(sticker_id)


@dp.message_handler()
async def echo(message: types.Message):
	await message.answer(message.text)


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)