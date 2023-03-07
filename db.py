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


def sync_get_account_list(uid: int) -> List[str]:
    user = get_or_create(uid)
    return [i.phone for i in BotAndAccount.select().where(BotAndAccount.uid == uid)]


async def get_info(uid: int, phone: str):
    account = BotAndAccount.select().where(
        (BotAndAccount.uid == uid) |
        (BotAndAccount.phone == phone)
    )
    if account:
        return account[0].url, account[0].status, "asdsads" #account[0].open_channel
    else:
        return None, None, None


async def get_lang(uid: int) -> str:
    user = get_or_create(uid)
    return user[0].lang


async def add_account(client_info):
    password = client_info["password"]
    phone = client_info["phone"]
    proxy = client_info["proxy"]
    url = client_info["url"]
    uid = client_info["uid"]

    BotAndAccount(
        uid=uid,
        phone=phone,
        url=url,
        proxy=proxy,
        password=password,
        type_proxy=proxy.split(":")[0]
    ).save()
    return
