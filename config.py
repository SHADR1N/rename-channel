import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
PASSWORD_BOT = os.getenv("PASSWORD_BOT")

message_dict = {
    "ru": {
        "code": "Введите пароль для доступа:",
        "viewBot": "Список аккаунтов",
        "newAccount": "Добавить аккаунт",
        "viewLog": "Информация о каналах",
        "main_menu": "Главное меню",
        "have_accs": "Выберите аккаунт:",
        "havnt_accs": "У вас нет аккаунтов.",
        "type_phone": "Введите н. телефона:",

        "type_proxy": "Пример добавления прокси:\n\ntype:ip:port:login:password\ntype:ip:port\nsocks5:127.0.0.1:8000:" \
        "username:password\n\nВведите прокси для аккаунта:",

        "type_password": "Если аккаунт имеет пароль, введите пароль 2FA:",
        "havnt_password": "Аккаунт без пароля",
        "type_url": "Введите ссылку на канал:",
        "wait_code": "На ваш аккаунт отправлен код авторизации, пришлите его при получении:",
        "good_add": "Аккаунт успешно добавлен.",
        "bad_auth": "Не смог авторизоваться. Попробуйте сменить прокси или пришлите код и попробуйте снова:",
        "wait_auth": "Запрашиваю авторизацию...",
        "bad_requesting": "Не удачная попытка авторизации, пришлите ссылку на канал и повторите попытку:",
        "get_auth": "Авторизуюсь...",
        "view_profile": "Phone: {PHONE}\nStatus: {STATUS}\nLink: {LINK}",
    },

    "en": {
        "view_profile": "Phone: {PHONE}\nStatus: {STATUS}\nLink: {LINK}",
        "get_auth": "Authorize...",
        "bad_requesting": "Unsuccessful login attempt, send link to channel and try again:",
        "code": "Enter password to access:",
        "viewBot": "List of accounts",
        "newAccount": "Add account",
        "viewLog": "Channel information",
        "main_menu": "Main menu",
        "have_accs": "Select an account:",
        "havnt_accs": "You have no accounts.",
        "type_phone": "Enter the phone number:",
        "type_proxy": """Example of adding a proxy:

type:ip:port:login:password
type:ip:port
socks5:127.0.0.1:8000:username:password

Enter a proxy for the account:""",
        "type_password": "If the account has a password, enter the 2FA password:",
        "havnt_password": "Account without password",
        "type_url": "Enter the link to the channel:",
        "wait_code": "An authorization code was sent to your account, send it when you receive it:",
        "good_add": "The account has been successfully added.",
        "bad_auth": "Couldn't log in. Try changing your proxy or send code and try again:",
        "wait_auth": "Requesting authorization..."
    }
}
