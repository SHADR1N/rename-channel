import asyncio
import json
import logging
import traceback

from aiogram.contrib.fsm_storage.memory import MemoryStorage

from config import TELEGRAM_TOKEN, PASSWORD_BOT, message_dict

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

from db import get_or_create, get_role, set_role, set_lang, get_lang, \
    get_account_list, add_account, sync_get_account_list, get_info, delete_account_db, all_account_list

from workers_telethon import create_client, success_code, run_phone, stop_phone, clients_phone

# logging.basicConfig(level=logging.DEBUG)

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


send_notify = asyncio.Queue()


async def send_queue(send_notify):
    while True:
        text = await send_notify.get()
        js_text = json.loads(text)
        uid = js_text["uid"]
        message = js_text["message"]
        await bot.send_message(uid, message)


async def run_is_true_account():
    for acc in await all_account_list():
        await run_phone(acc.phone, acc.uid, send_notify)


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
    link, status, open_channel, delay, close_url = await get_info(uid, phone)
    if link is not None and status is not None and open_channel is not None:
        msg = msg.replace("{PHONE}", phone)
        msg = msg.replace("{LINK}", link)

        if status:
            status = "Power On"
            START_STOP = "Stop account"
        else:
            status = "Power Off"
            START_STOP = "Run account"

        if open_channel:
            open_channel = "Open"
        else:
            open_channel = "Close"

        msg = msg.replace("{STATUS}", str(status))
        msg = msg.replace("{TYPE}", open_channel)
        msg = msg.replace("{TIMEOUT}", str(delay))
        msg = msg.replace("{LINK_CLOSE}", close_url)

    else:
        return await callback.answer()
    await callback.answer()

    if open_channel:
        OPEN_CLOSE = "Close channel"
    else:
        OPEN_CLOSE = "Open channel"

    knb = types.InlineKeyboardMarkup(row_width=2)
    knb.add(*[
        types.InlineKeyboardButton(text=START_STOP, callback_data=f"run__{phone}"),
        types.InlineKeyboardButton(text=OPEN_CLOSE, callback_data=f"open__{phone}")
    ])
    knb.add(types.InlineKeyboardButton(text="Delete", callback_data=f"delete__{phone}"))
    knb.add(types.InlineKeyboardButton(text="Back", callback_data="back to list account"))

    return await callback.message.reply(msg, reply_markup=knb)


@dp.callback_query_handler(lambda callback: str(callback.data).startswith("delete__"))
async def delete_account(callback: types.CallbackQuery):
    """

    :type callback: object
    """
    uid = callback.from_user.id
    data = callback.data
    phone = str(data).split("delete__")[1]
    await delete_account_db(phone, uid)
    return await callback.message.reply("Deleted.")


@dp.callback_query_handler(lambda callback: str(callback.data).startswith("run__"))
async def run_account(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = callback.data
    phone = str(data).split("run__")[1]
    lang = await get_lang(uid)
    link, status, open_channel, _, _ = await get_info(uid, phone)

    await callback.message.delete()
    if status is False:
        try:
            await run_phone(phone, uid, send_notify)
        except:
            print(traceback.format_exc())
            msg = message_dict[lang]["error_start"]
            return await bot.send_message(uid, msg)
        else:
            msg = message_dict[lang]["good_start"]
            return await bot.send_message(uid, msg)

    else:
        msg = message_dict[lang]["good_stop"]
        await stop_phone(phone, uid)
        return await bot.send_message(uid, msg)


@dp.callback_query_handler(lambda callback: str(callback.data).startswith("open__"))
async def open_account(callback: types.CallbackQuery):
    uid = callback.from_user.id
    data = callback.data
    phone = str(data).split("open__")[1]
    lang = await get_lang(uid)
    link, status, open_channel, _, _ = await get_info(uid, phone)

    await callback.message.delete()
    if status is False:
        msh = message_dict[lang]["bot_off"]
        await bot.send_message(uid, msh)
        return await callback.answer()

    obj = clients_phone[uid][phone]
    if open_channel:
        await obj.set_open_close(False)
    else:
        await obj.set_open_close(True)
    return await bot.send_message(uid, "Task processing...")


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
        if len(await all_account_list(uid)) >= 10:
            return await bot.send_message(uid, "You can add a maximum of 10 accounts.")

        await NewAccount.proxy.set()
        msg = message_dict[lang]["type_proxy"]
        return await bot.send_message(uid, msg, reply_markup=cancel_btn)

    if message_text in [message_dict[la]["viewLog"] for la in ["ru", "en"]]:
        infos = await all_account_list(uid)

        message = []
        for info in infos:
            message.append(
                f"Phone: {info.phone}\nUrl: @{info.url}\nPrivate url: {info.close_url}"
            )
        message = "\n".join(message)

        return await bot.send_message(uid, "Your accounts:\n\n" + message)

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
    loop = asyncio.get_event_loop()
    loop.create_task(send_queue(send_notify))
    loop.create_task(run_is_true_account())
    executor.start_polling(dp, skip_updates=True, loop=loop)
