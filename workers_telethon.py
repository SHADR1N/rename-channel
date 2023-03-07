from telethon import TelegramClient


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

    await client.sign_in(
        password=password,
        phone_code_hash=phone_code_hash,
        phone=phone,
        code=code
    )

    if await client.is_user_authorized():
        pass
    else:
        raise ValueError
    return await client.disconnect()

