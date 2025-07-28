import asyncio
from telethon import TelegramClient, events, functions, types
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from colorama import Fore, Style, init

init()  # Инициализация colorama для цветного вывода

class TelegramConsoleClient:
    def __init__(self):
        self.api_id = 111111  # Замените на ваш API ID
        self.api_hash = '111111'  # Замените на ваш API Hash
        self.session_file = 'fastgramdesktop_session'  # Имя файла сессии
        self.client = None
        self.chats = []
        self.selected_chat = None
        self.unread_messages = []
        self.running = True

    async def start(self):
        print(f"{Fore.YELLOW}FastGram{Style.RESET_ALL}")
        print("1. Войти в существующий аккаунт")
        print("2. Зарегистрировать новый аккаунт")
        choice = input("Выберите действие: ")

        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
        
        try:
            if choice == '1':
                await self.login_existing()
            elif choice == '2':
                await self.register_new()
            else:
                print(f"{Fore.RED}Неверный выбор{Style.RESET_ALL}")
                return

            self.client.add_event_handler(self.handle_new_message, events.NewMessage)
            asyncio.create_task(self.message_updater())
            await self.main_loop()
        finally:
            await self.client.disconnect()

    async def login_existing(self):
        await self.client.start(
            phone=lambda: input("Введите номер телефона: "),
            password=lambda: input("Введите пароль двухэтапной аутентификации (если есть): ")
        )
        print(f"{Fore.GREEN}Успешная авторизация!{Style.RESET_ALL}")
        await self.load_dialogs()

    async def register_new(self):
        print(f"\n{Fore.CYAN}Регистрация нового аккаунта Telegram{Style.RESET_ALL}")
        phone_number = input("Введите номер телефона (с кодом страны): ")
        first_name = input("Введите имя: ")
        last_name = input("Введите фамилию (необязательно): ")

        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(phone_number)
            code = input("Введите код подтверждения из SMS/Telegram: ")
            
            try:
                await self.client.sign_in(phone_number, code)
            except Exception as e:
                if "two-steps" in str(e):
                    password = input("Введите пароль двухэтапной аутентификации: ")
                    await self.client.sign_in(password=password)

        await self.client(functions.account.UpdateProfileRequest(
            first_name=first_name,
            last_name=last_name if last_name else ""
        ))
        
        print(f"\n{Fore.GREEN}Регистрация успешно завершена!{Style.RESET_ALL}")
        await self.load_dialogs()

    async def load_dialogs(self):
        try:
            result = await self.client(GetDialogsRequest(
                offset_date=None,
                offset_id=0,
                offset_peer=InputPeerEmpty(),
                limit=100,
                hash=0
            ))
            
            self.chats = []
            for chat in result.chats:
                self.chats.append(chat)
            for user in result.users:
                if getattr(user, 'bot', False) or getattr(user, 'is_self', False):
                    continue
                self.chats.append(user)
            
            print(f"\n{Fore.YELLOW}Список чатов/каналов:{Style.RESET_ALL}")
            for i, chat in enumerate(self.chats):
                name = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Unknown"
                print(f"{i}: {name}")
        except Exception as e:
            print(f"{Fore.RED}Ошибка при загрузке диалогов: {e}{Style.RESET_ALL}")

    async def message_updater(self):
        while self.running:
            try:
                if self.selected_chat:
                    await self.check_new_messages()
                await asyncio.sleep(2)
            except Exception as e:
                print(f"{Fore.RED}Ошибка в message_updater: {e}{Style.RESET_ALL}")
                await asyncio.sleep(5)

    async def check_new_messages(self):
        last_message_id = self.unread_messages[-1].id if self.unread_messages else 0
        
        new_messages = []
        async for message in self.client.iter_messages(
            self.selected_chat,
            limit=10,
            min_id=last_message_id
        ):
            if message.id > last_message_id and message.message:
                new_messages.append(message)
        
        if new_messages:
            self.unread_messages.extend(new_messages)
            await self.print_messages(new_messages)

    async def print_messages(self, messages):
        """Выводит сообщения с форматированием"""
        # Преобразуем в список, если это итератор
        messages_list = list(messages) if not isinstance(messages, list) else messages
        
        for msg in reversed(messages_list):
            sender = await msg.get_sender()
            name = getattr(sender, 'first_name', getattr(sender, 'title', 'Unknown'))
            date = msg.date.strftime("%H:%M")
            
            if msg.out:
                print(f"{Fore.GREEN}[{date}] Вы: {msg.message}{Style.RESET_ALL}")
            else:
                print(f"{Fore.BLUE}[{date}] {name}: {msg.message}{Style.RESET_ALL}")

    async def select_chat(self):
        chat_index = input("Введите номер чата: ")
        try:
            chat_index = int(chat_index)
            if 0 <= chat_index < len(self.chats):
                self.selected_chat = self.chats[chat_index]
                chat_name = getattr(self.selected_chat, 'title', 
                                  getattr(self.selected_chat, 'first_name', 'Unknown'))
                print(f"\n{Fore.YELLOW}Выбран чат: {chat_name}{Style.RESET_ALL}")
                
                # Получаем сообщения и сохраняем как список
                self.unread_messages = []
                messages = []
                async for message in self.client.iter_messages(self.selected_chat, limit=50):
                    if message.message:
                        messages.append(message)
                
                self.unread_messages = messages
                print(f"{Fore.CYAN}\nПоследние сообщения:{Style.RESET_ALL}")
                await self.print_messages(self.unread_messages.copy())  # Используем копию списка
                print(f"{Fore.CYAN}{'-'*50}{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}Неверный номер чата.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Введите число.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Ошибка при загрузке сообщений: {e}{Style.RESET_ALL}")

    async def send_message(self):
        if not self.selected_chat:
            print(f"{Fore.RED}Сначала выберите чат.{Style.RESET_ALL}")
            return
        
        try:
            message = input("Введите сообщение (или 'q' для отмены): ")
            if message.lower() == 'q':
                return
                
            if message:
                await self.client.send_message(self.selected_chat, message)
                print(f"{Fore.GREEN}Сообщение отправлено!{Style.RESET_ALL}")
                await self.check_new_messages()
        except Exception as e:
            print(f"{Fore.RED}Ошибка при отправке: {e}{Style.RESET_ALL}")

    async def handle_new_message(self, event):
        if (self.selected_chat and 
            event.chat_id == getattr(self.selected_chat, 'id', None) and
            event.message.message and not event.message.out):
            
            self.unread_messages.append(event.message)
            await self.print_messages([event.message])

    async def main_loop(self):
        while self.running:
            print(f"\n{Fore.YELLOW}Меню:{Style.RESET_ALL}")
            print("1: Выбрать чат/канал")
            print("2: Отправить сообщение")
            print("3: Обновить список чатов")
            print("4: Выход")
            
            if self.selected_chat:
                chat_name = getattr(self.selected_chat, 'title', 
                                  getattr(self.selected_chat, 'first_name', ''))
                print(f"\n{Fore.CYAN}Текущий чат: {chat_name}{Style.RESET_ALL}")
            
            try:
                choice = input("Выберите действие: ")
                
                if choice == '1':
                    await self.select_chat()
                elif choice == '2':
                    await self.send_message()
                elif choice == '3':
                    await self.load_dialogs()
                elif choice == '4':
                    self.running = False
                    print(f"{Fore.YELLOW}Выход...{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Неверный выбор, попробуйте снова.{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Ошибка: {e}{Style.RESET_ALL}")

if __name__ == '__main__':
    client = TelegramConsoleClient()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(client.start())
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
    finally:
        loop.close()
