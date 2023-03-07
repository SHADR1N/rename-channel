import logging
import traceback

from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import TELEGRAM_TOKEN, PASSWORD_BOT, message_dict

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from db import get_or_create, get_role, set_role, set_lang, get_lang, \
    get_account_list, add_account, sync_get_account_list, get_info

from workers_telethon import create_client, success_code

logging.basicConfig(level=logging.DEBUG)

storage = MemoryStorage()
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot, storage=storage)


uid_client = {}
cancel_btn = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
cancel_btn.add(types.KeyboardButton(text="Cancel"))


class NewAccount(StatesGroup):
    proxy = State()
    phone = State()
    password = State()
    url = State()
    code = State()


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    uid = message.from_user.id
    get_or_create(uid)

    knb = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    knb.add(types.KeyboardButton(text="🇷🇺 RUS"))
    knb.add(types.KeyboardButton(text="🇺🇸 ENG"))
    return await bot.send_message(uid, "☑️Select language bot:", reply_markup=knb)


@dp.message_handler(lambda message: message.text in ["🇷🇺 RUS", "🇺🇸 ENG"])
async def select_lang(message: types.Message):
    uid = message.from_user.id
    if "RUS" in message.text:
        lang = "ru"
    else:
        lang = "en"

    await set_lang(uid, lang)
    msg = message_dict[lang]

    if get_role(uid) == "any":
        return await bot.send_message(uid, msg["code"])
    else:
        knb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        knb.add(
            *[
                types.KeyboardButton(text=msg["viewBot"]),
                types.KeyboardButton(text=msg["newAccount"])
            ]
        )
        knb.add(types.KeyboardButton(text=msg["viewLog"]))
        return await bot.send_message(uid, text=msg["main_menu"], reply_markup=knb)


@dp.message_handler(lambda message: message.text == PASSWORD_BOT)
async def get_access(message: types.Message):
    uid = message.from_user.id
    await set_role(uid)
    lang = await get_lang(uid)
    msg = message_dict[lang]

    knb = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    knb.add(
        *[
            types.KeyboardButton(text=msg["viewBot"]),
            types.KeyboardButton(text=msg["newAccount"])
        ]
    )
    knb.add(types.KeyboardButton(text=msg["viewLog"]))
    return await bot.send_message(uid, text=msg["main_menu"], reply_markup=knb)


@dp.callback_query_handler(lambda callback: callback.data in sync_get_account_list(callback.from_user.id))
async def select_account(callback: types.CallbackQuery):
    phone = callback.data
    uid = callback.from_user.id
    lang = await get_lang(uid)

    msg = message_dict[lang]["view_profile"]
    link, status, open_channel = await get_info(uid, phone)
    if link is not None and status is not None and open_channel is not None:
        msg = msg.replace("{PHONE}", phone)
        msg = msg.replace("{LINK}", link)

        if status:
            status = "Power On"
        else:
            status = "Power Off"

        msg = msg.replace("{STATUS}", str(status))

    if status:
        START_STOP = "Stop account"
    else:
        START_STOP = "Run account"

    if open_channel:
        OPEN_CLOSE = "Close channel"
    else:
        OPEN_CLOSE = "Open channel"

    knb = types.InlineKeyboardMarkup(row_width=2)
    knb.add(*[
        types.InlineKeyboardButton(text=START_STOP, callback_data=f"run__{phone}"),
        types.InlineKeyboardButton(text=OPEN_CLOSE, callback_data=f"open__{phone}")
    ])
    knb.add(types.InlineKeyboardButton(text="Back", callback_data="back to list account"))

    return await callback.message.reply(msg, reply_markup=knb)


@dp.callback_query_handler(lambda callback: callback.data)
async def select_account(callback: types.CallbackQuery):
    phone = callback.data
    uid = callback.from_user.id
    lang = await get_lang(uid)

    if callback.data == "back to list account":
        account_list = await get_account_list(uid)

        if not account_list:
            msg = message_dict[lang]["havnt_accs"]
        else:
            msg = message_dict[lang]["have_accs"]

        knb = types.InlineKeyboardMarkup(row_width=1)
        knb.add(
            *[types.InlineKeyboardButton(text=name, callback_data=name) for name in account_list]
        )
        return await bot.send_message(uid, msg, reply_markup=knb)


@dp.message_handler(lambda message: get_role(message.from_user.id) == "admin")
async def main_logic_bot(message: types.Message):
    uid = message.from_user.id
    message_text = message.text
    lang = await get_lang(uid)

    if message_text in [message_dict[la]["viewBot"] for la in ["ru", "en"]]:
        account_list = await get_account_list(uid)

        if not account_list:
            msg = message_dict[lang]["havnt_accs"]
        else:
            msg = message_dict[lang]["have_accs"]

        knb = types.InlineKeyboardMarkup(row_width=1)
        knb.add(
            *[types.InlineKeyboardButton(text=name, callback_data=name) for name in account_list]
        )
        return await bot.send_message(uid, msg, reply_markup=knb)

    if message_text in [message_dict[la]["newAccount"] for la in ["ru", "en"]]:
        await NewAccount.proxy.set()
        msg = message_dict[lang]["type_proxy"]
        return await bot.send_message(uid, msg, reply_markup=cancel_btn)

    if message_text in [message_dict[la]["viewLog"] for la in ["ru", "en"]]:
        return await bot.send_message(uid, "3")

    else:
        return await select_lang(message)


@dp.message_handler(state=NewAccount.proxy)
async def state_proxy(message: types.Message, state: FSMContext):
    if message.text == "Cancel":
        await select_lang(message)
        return await state.finish()

    async with state.proxy() as data:
        data['proxy'] = message.text

    uid = message.from_user.id
    lang = await get_lang(uid)
    msg = message_dict[lang]["type_phone"]
    await NewAccount.next()
    return await message.reply(msg, reply_markup=cancel_btn)


@dp.message_handler(state=NewAccount.phone)
async def state_phone(message: types.Message, state: FSMContext):
    if message.text == "Cancel":
        await select_lang(message)
        return await state.finish()

    async with state.proxy() as data:
        data['phone'] = message.text

    uid = message.from_user.id
    lang = await get_lang(uid)
    msg = message_dict[lang]["type_password"]
    msg_kb = message_dict[lang]["havnt_password"]
    await NewAccount.next()

    knb = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    knb.add(types.KeyboardButton(text=msg_kb))
    knb.add(types.KeyboardButton(text="Cancel"))
    return await message.reply(msg, reply_markup=knb)


@dp.message_handler(state=NewAccount.password)
async def state_proxy(message: types.Message, state: FSMContext):
    if message.text == "Cancel":
        await select_lang(message)
        return await state.finish()

    uid = message.from_user.id
    lang = await get_lang(uid)

    async with state.proxy() as data:
        if message.text in [message_dict[i]["havnt_password"] for i in ["ru", "en"]]:
            data["password"] = None
        else:
            data['password'] = message.text

    msg = message_dict[lang]["type_url"]
    await NewAccount.next()
    return await message.reply(msg, reply_markup=cancel_btn)


@dp.message_handler(state=NewAccount.url)
async def state_proxy(message: types.Message, state: FSMContext):
    if message.text == "Cancel":
        await select_lang(message)
        return await state.finish()

    uid = message.from_user.id
    lang = await get_lang(uid)

    data = await state.get_data()

    proxy = data["proxy"]
    phone = data["phone"]
    password = data["password"]

    msg = message_dict[lang]["wait_auth"]
    await message.reply(msg)
    try:
        client, phone_code_hash = await create_client(phone, proxy, password)
    except:
        print(traceback.format_exc())
        msg = message_dict[lang]["bad_requesting"]
        return await message.reply(msg, reply_markup=cancel_btn)

    uid_client[str(uid)] = [client, phone_code_hash]
    async with state.proxy() as data:
        data['url'] = message.text

    msg = message_dict[lang]["wait_code"]
    await NewAccount.code.set()
    return await message.reply(msg, reply_markup=cancel_btn)


@dp.message_handler(state=NewAccount.code)
async def state_proxy(message: types.Message, state: FSMContext):
    if message.text == "Cancel":
        await select_lang(message)
        return await state.finish()

    uid = message.from_user.id
    lang = await get_lang(uid)

    async with state.proxy() as data:
        data["code"] = message.text

    data = await state.get_data()

    proxy = data["proxy"]
    phone = data["phone"]
    url = data["url"]
    password = data["password"]
    code = data["code"]
    client = uid_client[str(uid)]

    client_info = {
        "client": client,
        "code": code,
        "password": password,
        "phone": phone,
        "url": url,
        "proxy": proxy,
        "uid": uid
    }

    msg = message_dict[lang]["get_auth"]
    await message.reply(msg)
    try:
        await success_code(client_info)
    except:
        print(traceback.format_exc())
        msg = message_dict[lang]["bad_auth"]
        await message.reply(msg, reply_markup=cancel_btn)
        return await state.finish()

    await add_account(client_info)
    msg = message_dict[lang]["good_add"]
    await message.reply(msg, reply_markup=cancel_btn)
    await select_lang(message)
    return await state.finish()


@dp.message_handler(lambda message: get_role(message.from_user.id) == "any")
async def access_denied(message: types.Message):
    uid = message.from_user.id
    return await bot.send_message(uid, "Access denied.")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
