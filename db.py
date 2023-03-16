from typing import List

import peewee

from models import User, BotAndAccount


def get_or_create(uid: int) -> peewee.Model:
    return User.get_or_create(uid=uid)


def get_role(uid: int) -> peewee.Model:
    user = get_or_create(uid)
    return user[0].role


async def set_role(uid: int) -> bool:
    user = get_or_create(uid)
    user[0].role = "admin"
    user[0].save()
    return True


async def set_lang(uid: int, lang: str) -> bool:
    user = get_or_create(uid)
    user[0].lang = lang
    user[0].save()
    return True


async def get_account_list(uid: int) -> List[str]:
    user = get_or_create(uid)
    return [i.phone for i in BotAndAccount.select().where(BotAndAccount.uid == uid)]


async def all_account_list(uid: int = None):
    if uid is None:
        return BotAndAccount.select().where(BotAndAccount.status == True)
    else:
        user = get_or_create(uid)
        return BotAndAccount.select().where(BotAndAccount.uid == uid)


async def set_private_channel(phone, uid, status):
    obj = BotAndAccount.select().where(BotAndAccount.uid == uid, BotAndAccount.phone == phone)
    if obj:
        obj = obj[0]
        obj.open_channel = status
        obj.save()


def sync_get_account_list(uid: int) -> List[str]:
    user = get_or_create(uid)
    return [i.phone for i in BotAndAccount.select().where(BotAndAccount.uid == uid)]


async def get_info(uid: int, phone: str):
    account = BotAndAccount.select().where(
        (BotAndAccount.uid == uid) |
        (BotAndAccount.phone == phone)
    )
    if account:
        return account[0].url, account[0].status, account[0].open_channel, account[0].delay_before_rename, account[
            0].close_url, account[0].banned
    else:
        return None, None, None


async def get_lang(uid: int) -> str:
    user = get_or_create(uid)
    return user[0].lang


async def get_proxy(phone, uid):
    obj = BotAndAccount.select().where(BotAndAccount.uid == uid, BotAndAccount.phone == phone)
    if obj:
        return obj[0].proxy
    else:
        return None


async def account_is_bad(phone, uid):
    obj = BotAndAccount.select().where(BotAndAccount.phone == phone, BotAndAccount.uid == uid)
    if obj:
        obj[0].banned = True
        obj[0].status = False
        obj[0].save()
    return


async def phone_is_auth(phone, uid, status):
    obj = BotAndAccount.select().where(BotAndAccount.phone == phone, BotAndAccount.uid == uid)
    if obj:
        obj[0].status = status
        obj[0].save()
    return


def get_timer(phone, uid):
    obj = BotAndAccount.select().where(BotAndAccount.phone == phone, BotAndAccount.uid == uid)
    if obj:
        return obj[0].delay_before_rename, obj[0].uid_channel, obj[0].url, obj[0].open_channel, obj[0].close_url
    else:
        return 100, None, None


async def edit_url_chat(address, phone, uid, close=False):
    obj = BotAndAccount.select().where(BotAndAccount.phone == phone, BotAndAccount.uid == uid)
    if obj:
        obj = obj[0]
        if close:
            obj.close_url = address
            obj.url = ""
            obj.open_channel = False
        else:
            obj.url = address
            obj.close_url = ""
            obj.open_channel = True
        obj.save()


async def edit_uid_chat(phone, uid, channel_id):
    obj = BotAndAccount.select().where(BotAndAccount.phone == phone, BotAndAccount.uid == uid)
    if obj:
        obj = obj[0]
        obj.uid_channel = channel_id
        obj.save()


async def delete_account_db(phone, uid):
    obj = BotAndAccount.select().where(BotAndAccount.phone == phone, BotAndAccount.uid == uid)
    if obj:
        obj = obj[0]
        obj.delete_instance()


async def add_account(client_info):
    password = client_info["password"]
    phone = client_info["phone"]
    proxy = client_info["proxy"]
    url = client_info["url"]
    uid = client_info["uid"]
    delay = client_info["delay"]

    BotAndAccount(
        uid=uid,
        delay_before_rename=delay,
        phone=phone,
        url=url,
        proxy=proxy,
        password=password,
        type_proxy=proxy.split(":")[0]
    ).save()
    return
