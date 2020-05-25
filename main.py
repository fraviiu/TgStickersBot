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
loop.create_task(actions.main()) 


bot = Bot(token=config.token, loop=loop, proxy=config.proxy_url)
dp = Dispatcher(bot, storage=MemoryStorage())


class SUser(StatesGroup):
	nick = State()


class SSticker(StatesGroup):
	sticker = State()
	name = State()
	delete = State()


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
		about_text = f'Ваш id: {user.chat_id}\
		\nВаш ник: {emojize(user.nick)}\
		\nВаш опыт: {user.score}'
		await message.answer(about_text,
			reply_markup=markup)
	except User.DoesNotExist:
		await message.answer('Вы ещё не создали профиль, напишите свой никнейм')
		await SUser.nick.set()


@dp.message_handler(state=SUser.nick, content_types=types.ContentTypes.TEXT)
async def nick_user(message: types.Message, state: FSMContext):
	if await check_nick(message):
		return
	if User.select().where(User.chat_id == message.chat.id):
		user = User.get(chat_id=message.chat.id)
		user.update(nick=message.text).execute()
		await message.answer('Ник успешно изменен')
	else:
		user = User.create(chat_id=message.chat.id, nick=demojize(message.text))
		await message.answer('Профиль создан успешно')
	await about_user(message)
	await state.finish()


@dp.callback_query_handler(lambda call: call.data == 'edit')
async def about_edit_nick(call: types.CallbackQuery):
	await call.message.edit_text('Введите новый никнейм') 
	await SUser.nick.set()


@dp.message_handler(commands='sticker')
async def about_sticker(message: types.Message):
	try:
		user = User.get(chat_id=message.chat.id)
		await message.answer('Отправьте мне ваш стикер')
		await SSticker.sticker.set()
	except User.DoesNotExist:
		await message.answer('Вам нужен профиль для создания стикера')


@dp.message_handler(commands='del')
async def del_sticker(message: types.Message):
	try:
		user = User.get(chat_id=message.chat.id)
	except User.DoesNotExist:
		await message.answer('Вам нужен профиль для создания стикера')
		return
	for stick in Sticker.select().where(Sticker.author == user):
		await message.answer(f'id: {stick.id}')
		await send_stick(message, stick)
	await message.answer('Напишите id стикера для удаления')
	await SSticker.delete.set()


@dp.message_handler(commands='sticks')
async def all_stickers(message: types.Message):
	stickers = Sticker.select()
	if not stickers:
		await message.answer('Ещё не существует ни одного стикера')
		return
	for stick in stickers:
		await send_stick(message, stick)


async def send_stick(message: types.Message, stick: Sticker):
	await message.answer(f'{stick.name}\nАвтор: {stick.author.nick}')
	await message.answer_sticker(stick.sticker)


@dp.message_handler(state=SSticker.sticker, content_types=types.ContentTypes.STICKER)
async def create_sticker(message: types.Message, state: FSMContext):
	if Sticker.select().where(Sticker.stick_uniq == message.sticker.file_unique_id):
		await message.answer('Такой стикер уже существует')
		stick = Sticker.get(stick_uniq=message.sticker.file_unique_id)
		await send_stick(message, stick)
		state.finish()
		return
	await state.update_data(sticker_id=message.sticker.file_id,
		sticker_uniq_id=message.sticker.file_unique_id)
	await message.answer('Придумайте название для стикера')
	await SSticker.name.set()


@dp.message_handler(state=SSticker.name, content_types=types.ContentTypes.TEXT)
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
	await message.answer(f'Стикер {name} создан успешно\nid:')
	await message.answer(Sticker.get(stick_uniq=data['sticker_uniq_id']).id)
	await message.answer_sticker(data['sticker_id'])


@dp.message_handler(state=SSticker.delete, content_types=types.ContentTypes.TEXT)
async def delete_sticker(message: types.Message, state: FSMContext):
	if not message.text.isdigit():
		await message.answer('id состоит из цифр если что))')
		return
	try:
		Sticker.get(id=message.text).delete_instance()
	except Sticker.DoesNotExist:
		await message.answer(f'стикера с id: {message.text} - не существует')
		return
	await state.finish()
	await message.answer('Стикер успешно удален')


@dp.message_handler(content_types=types.ContentTypes.STICKER)
async def get_sticker(message: types.Message):
	try: 
		stick = Sticker.get(stick_uniq=message.sticker.file_unique_id)
	except Sticker.DoesNotExist:
		await message.answer('К сожелению такова стикера нету')
		return
	await send_stick(message, stick)


@dp.message_handler(commands=['start'])
async def welcome(message: types.Message):
	first = message.chat.first_name
	last = message.chat.last_name
	await message.answer(f'Привет, {first} {last}')


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)