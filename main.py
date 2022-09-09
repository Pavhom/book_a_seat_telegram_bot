from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.types import ParseMode
from datetime import datetime
import aiogram.utils.markdown as md
import logging
import sqlite3
from config import *


logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

conn = sqlite3.connect('datab.db')
cur = conn.cursor()


class UserOrderForm(StatesGroup):
    date = State()
    name = State()
    phone = State()


# admin buttons
kb_admin = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_admin.add(types.InlineKeyboardButton(text="/order"))

# client buttons
kb_client = types.ReplyKeyboardMarkup(resize_keyboard=True)
kb_client.add(types.InlineKeyboardButton(text="Замовити місце"))


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    if message.from_user.id == ADMIN:
        await message.answer('Доброго дня, ADMIN!', reply_markup=kb_admin)
    else:
        await message.answer(f'Доброго дня, {message.from_user.first_name}!', reply_markup=kb_client)


@dp.message_handler(commands=['order'])
async def order(message: types.Message):
    cur.execute('''SELECT * FROM orders''')
    results = cur.fetchall()
    if message.from_user.id == ADMIN:
        data_from_db = ''
        for row in results:
            data_from_db = data_from_db + f'{str(row[1]).split(".")[0]} ::: {row[2]} - {row[3]} - {row[4]}\n'
        await bot.send_message(message.chat.id, data_from_db)


@dp.message_handler(content_types=['text'])
async def add_order(message: types.Message):
    otm = types.ReplyKeyboardMarkup(resize_keyboard=True)
    otm.add(types.InlineKeyboardButton(text="Відміна"))
    if message.text == 'Замовити місце':
        await UserOrderForm.date.set()
        await message.reply('Вкажіть дату поїздки', reply_markup=otm)


# order cancellation
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='Відміна', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('ОК', reply_markup=kb_client)


@dp.message_handler(state=UserOrderForm.date)
async def input_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['date'] = message.text
        print("Дата", data['date'])
    await UserOrderForm.name.set()
    await message.reply('Вкажіть ваше ПІБ')


@dp.message_handler(state=UserOrderForm.name)
async def input_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
        print("Імя", data['name'])
    await UserOrderForm.phone.set()
    await message.reply('Вкажіть ваш номер телефону')


@dp.message_handler(state=UserOrderForm.phone)
async def input_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.text
        print("Телефон", data['phone'])
    await UserOrderForm.phone.set()
    await message.reply('Інформацію збережено. Очікуйте дзвінок для підтвердження', reply_markup=kb_client)
    await bot.send_message(
        message.chat.id,
        md.text(md.text('Ваше замовлення:',),
                md.text('Дата поїздки:', md.bold(data['date'])),
                md.text('ПІБ:', md.bold(data['name'])),
                md.text('Номер телефону:', md.bold(data['phone'])),
                sep='\n',),
        parse_mode=ParseMode.MARKDOWN,
    )
    cur.execute(f"INSERT INTO [orders] (date_added, date, name, phone) VALUES ('{datetime.now()}','{data['date']}','{data['name']}','{data['phone']}')")
    conn.commit()
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
