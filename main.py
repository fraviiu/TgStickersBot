import logging
import asyncio
import os

from aiogram import Bot, Dispatcher, types, executor
from aiogram.utils.emoji import emojize, demojize
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram import types
 
from models import User, Sticker
import config
import actions


logging.basicConfig(handlers=(logging.FileHandler(config.logsfile),
	logging.StreamHandler()), level=logging.INFO)

#кастомные задачи в асинхронщину
loop = asyncio.new_event_loop()
#loop.create_task(actions.main()) 


bot = Bot(token=config.token, loop=loop, proxy=config.proxy_url)
dp = Dispatcher(bot, storage=MemoryStorage())


class Profile(StatesGroup):
	nick = State()


class CreateStiker(StatesGroup):
	sticker = State()
	name = State()


async def check_nick(message: types.Message):
	if User.select().where(User.nick == message.text):
		await message.answer('Пользователь с таким ником уже существует, придумайте новый')
		return True
	if len(message.text) > User.nick.max_length:
		await message.answer(f'Минимальная длинна ника {User.nick.max_length}')
		return True
	return False


@dp.message_handler(commands='me')
async def about_user(message: types.Message):
	try:
		user = User.get(chat_id=message.chat.id)
		markup = types.InlineKeyboardMarkup()
		edit_butt = types.InlineKeyboardButton(text='Сменить никнейм',
			callback_data='edit')
		markup.add(edit_butt)
		await message.answer(f'Ваш id: {user.chat_id}\nВаш ник: {emojize(user.nick)}',
			reply_markup=markup)
	except User.DoesNotExist:
		await message.answer('Вы ещё не создали профиль, напишите свой никнейм')
		await Profile.nick.set()


@dp.message_handler(state=Profile.nick, content_types=types.ContentTypes.TEXT)
async def create_profile(message: types.Message, state: FSMContext):
	if await check_nick(message):
		return
	user = User.create(chat_id=message.chat.id, nick=demojize(message.text))
	await message.answer(f'Ваш id: {user.chat_id}\nВаш ник: {emojize(user.nick)}')
	await state.finish()


@dp.callback_query_handler(lambda call: call.data == 'edit')
async def about_edit_nick(call: types.CallbackQuery):
	await call.message.edit_text('Введите новый никнейм') 
	await Profile.nick.set()


@dp.message_handler(commands='sticker')
async def about_sticker(message: types.Message):
	try:
		user = User.get(chat_id=message.chat.id)
		await message.answer('Отправьте мне ваш стикер')
		await CreateStiker.sticker.set()
	except User.DoesNotExist:
		await message.answer('Вам нужен профиль для создания стикера')


@dp.message_handler(commands='sticks')
async def all_stickers(message: types.Message):
	for stick in Sticker.select():
		await send_stick(message, stick)


async def send_stick(message: types.Message, stick: Sticker):
	await message.answer(f'{stick.name}\nАвтор: {stick.author}')
	await message.answer_sticker(stick.sticker)


@dp.message_handler(state=CreateStiker.sticker, content_types=types.ContentTypes.STICKER)
async def create_sticker(message: types.Message, state: FSMContext):
	existing = Sticker.select().where(Sticker.stick_uniq == message.sticker.file_unique_id)
	if existing:
		await message.answer('Такой стикер уже существует')
		await send_stick(message, existing)
		return
	await state.update_data(sticker_id=message.sticker.file_id,
		sticker_uniq_id=message.sticker.file_unique_id)
	await message.answer('Придумайте название для стикера')
	await CreateStiker.next()


@dp.message_handler(state=CreateStiker.name, content_types=types.ContentTypes.TEXT)
async def name_sticker(message: types.Message, state: FSMContext):
	slen = Sticker.name.max_length
	if len(message.text) > slen:
		await message.answer(f'Минимальная длинна названия стикера - {slen} символов')
		return
	data = await state.get_data()
	name = message.text[0].upper() + message.text[1:]
	user = User.get(chat_id=message.chat.id)
	Sticker.create(sticker=data['sticker_id'], stick_uniq=data['sticker_uniq_id'],
		name=name, author=user)
	await state.finish()
	await message.answer(f'Стикер {name} создан успешно')
	await message.answer_sticker(data['sticker'])


@dp.message_handler(content_types=types.ContentTypes.STICKER)
async def n_sticker(message: types.Message):
	sticker_id = message.sticker.file_id
	await message.answer(sticker_id)
	await message.answer_sticker(sticker_id)
	await message.answer(message.sticker)


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)