import asyncio
import json
import random
import threading
import traceback
from time import time
from typing import Optional

from telethon import TelegramClient
from telethon.errors import rpcerrorlist
from telethon.tl.functions.channels import UpdateUsernameRequest, GetFullChannelRequest
from telethon import types
from db import get_proxy, set_private_channel, account_is_bad, phone_is_auth, get_timer, edit_uid_chat, edit_url_chat

clients_phone = {}


class TelethonRunApp:
    def __init__(self, phone, uid, send_notify):
        self.send_notify = send_notify
        self.client: Optional[TelegramClient] = None
        self.phone = phone
        self.uid = uid
        self.timer, self.chat_id, self.chat_url, self.open_channel, self.close_chat_url = get_timer(phone, uid)
        self.stop = False

    async def timeout_as(self, timer: int):
        start = time()
        open_channel = self.open_channel
        while start - time() < timer and self.stop is False:
            if self.open_channel != open_channel:
                break

            await asyncio.sleep(5)

    async def run_rename(self, client):
        chat = None
        chat_id = None
        chat_hash = None
        open_channel = self.open_channel
        while self.stop is False:
            try:
                if not self.chat_id:
                    chat = await client.get_entity(self.chat_url)

                    chat_id = self.chat_id = chat.id
                    chat_hash = chat.access_hash

                    await edit_uid_chat(self.phone, self.uid, self.chat_id)

                if not chat and self.chat_id:
                    if int(self.chat_id) > 0:
                        self.chat_id = "-100" + str(self.chat_id)
                    try:
                        chat = await client.get_entity(self.chat_id)
                    except:
                        if self.open_channel:
                            chat = await client.get_entity(self.chat_url)
                        else:
                            chat = await client.get_entity(self.close_chat_url)

                        chat_id = self.chat_id = chat.id
                        chat_hash = chat.access_hash

                        await edit_uid_chat(self.phone, self.uid, self.chat_id)

                    chat_id = self.chat_id = chat.id
                    chat_hash = chat.access_hash

                if open_channel != self.open_channel:
                    open_channel = self.open_channel
                    if self.open_channel is False:
                        await self.rename("", chat_id, chat_hash, client)
                        await set_private_channel(self.phone, self.uid, self.open_channel)
                        channelObject = types.InputChannel(
                            channel_id=chat_id,
                            access_hash=chat_hash)

                        # === ERROR BLOCK === #
                        export_channel = await self.client(GetFullChannelRequest(channelObject))
                        full_chat = export_channel.__dict__["full_chat"]
                        self.close_chat_url = full_chat.exported_invite.link
                        await edit_url_chat(self.close_chat_url, self.phone, self.uid, True)
                        await self.send_notify.put(str(json.dumps({
                            "uid": self.uid,
                            "message": f"Account: {self.phone}\nNew url: {self.close_chat_url}"
                        })))
                    else:
                        await self.rename(self.chat_url, chat_id, chat_hash, client)
                        await edit_url_chat(self.chat_url, self.phone, self.uid)
                        await self.send_notify.put(str(json.dumps({
                            "uid": self.uid,
                            "message": f"Account: {self.phone}\nNew url: {self.chat_url}"
                        })))

                if self.open_channel:

                    address = chat.username
                    if address:
                        if address[-4] == "_":
                            address = address[:-4]

                        address = address + "_" + ''.join(
                            [random.choice("qwertyuioasdfghjklzxcvbnm") for i in range(3)]
                        )
                        try:
                            if await client.is_user_authorized():
                                await self.rename(address, chat_id, chat_hash, client)
                                message = f"Account: {self.phone}\nChat: {self.chat_url}\n✅ Rename: @{address}"
                                await edit_url_chat(address, self.phone, self.uid)
                            else:
                                message = f"Account: {self.phone}\nChat: {self.chat_url}\n❌ Account is banned."

                        except rpcerrorlist.FloodWaitError as ex:
                            sec = ex.seconds
                            message = f"Account: {self.phone}\nChat: {self.chat_url}\n❌ Can't rename this channel. Flood wait error {sec} sec."

                        except:
                            print(traceback.format_exc())
                            message = f"Account: {self.phone}\nChat: {self.chat_url}\n❌ Can't rename this channel."

                        await self.send_notify.put(str(json.dumps({
                            "uid": self.uid,
                            "message": message
                        })))
            except:
                print(traceback.format_exc())

            await self.timeout_as(self.timer)

    async def rename(self, address, chat_id, chat_hash, client):
        res = await client(UpdateUsernameRequest(
            channel=types.InputChannel(
                channel_id=chat_id,
                access_hash=chat_hash)
            ,
            username=address))
        if res is True:
            return True
        else:
            raise ValueError

    async def set_open_close(self, status):
        self.open_channel = status

    @staticmethod
    async def convert_proxy(proxy):
        proxy = proxy.split(":")
        if len(proxy) == 3:
            proxy = {
                "proxy_type": proxy[0],
                "addr": proxy[1],
                "port": int(proxy[2])
            }
        else:
            proxy = {
                "proxy_type": proxy[0],
                "addr": proxy[1],
                "port": int(proxy[2]),
                "username": proxy[3],
                "password": proxy[4],
                "rdns": True
            }
        return proxy

    async def create_connect(self):
        async def _create_connect():
            proxy = await get_proxy(self.phone, self.uid)
            if proxy:

                proxy = await self.convert_proxy(proxy)
                self.client = TelegramClient(
                    f"accounts/{self.phone}",
                    api_id=6,
                    api_hash="eb06d4abfb49dc3eeb1aeb98ae0f581e",
                    proxy=proxy,
                    connection_retries=5,
                    auto_reconnect=True
                )
                await self.client.connect()
                if await self.client.is_user_authorized():
                    await self.client.start()
                    await self.run_rename(self.client)
                else:
                    await account_is_bad(self.phone, self.uid)
                    raise ValueError
            else:
                raise ValueError

        threading.Thread(target=asyncio.run, args=(_create_connect(),)).start()

    async def stop_connect(self):
        if self.client and await self.client.is_user_authorized():
            await self.client.disconnect()
        self.stop = True


async def run_phone(phone, uid, send_notify):
    if uid not in clients_phone:
        clients_phone[uid] = {}

    obj = TelethonRunApp(phone, uid, send_notify)
    await obj.create_connect()
    clients_phone[uid][phone] = obj
    await phone_is_auth(phone, uid, True)


async def stop_phone(phone, uid):
    if uid not in clients_phone:
        clients_phone[uid] = {}

    if phone in clients_phone[uid]:
        obj = clients_phone[uid][phone]
        await obj.stop_connect()
    await phone_is_auth(phone, uid, False)


async def create_client(phone, proxy, password):
    if isinstance(proxy, str):
        proxy = proxy.split("\n")[0]

        proxy = proxy.split(":")
        if len(proxy) == 3:
            proxy = {
                "proxy_type": proxy[0],
                "addr": proxy[1],
                "port": int(proxy[2])
            }
        else:
            proxy = {
                "proxy_type": proxy[0],
                "addr": proxy[1],
                "port": int(proxy[2]),
                "username": proxy[3],
                "password": proxy[4],
                "rdns": True
            }
    else:
        proxy = None

    client = TelegramClient(
        f"accounts/{phone}",
        api_id=6,
        api_hash="eb06d4abfb49dc3eeb1aeb98ae0f581e",
        proxy=proxy,
        connection_retries=5,
        auto_reconnect=True
    )
    await client.connect()
    res = await client.send_code_request(phone)
    return client, res.phone_code_hash


async def success_code(client_info: dict):
    client, phone_code_hash = client_info["client"]
    code = client_info["code"]
    password = client_info["password"]
    phone = client_info["phone"]
    print(password)

    try:
        await client.sign_in(
            password=password,
            phone_code_hash=phone_code_hash,
            phone=phone,
            code=code
        )
    except:
        await client.sign_in(password=password)

    if await client.is_user_authorized():
        await client.start()
    else:
        raise ValueError
    return await client.disconnect()
