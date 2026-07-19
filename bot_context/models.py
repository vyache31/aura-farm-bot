from dataclasses import dataclass

"""
Данные классы используются для формирования контекста
в группе, который в свою очередь добавляется
к запросе ИИ для генерации наиболее живого
ответа

Создайте в файле context/chat_info.py:

1. Строку bot_about c описанием личности вашего бота 
2. Строку chat_about с описанием вашего чата
3. Список chat_members из экземпляров класса Member,
предварительно заполнив нужную информацию;
"""

@dataclass
class Member:
    username: str
    name: str
    description: str
    relationship: str

@dataclass
class ChatMessage:
    username: str
    text: str
    reply_to_username: str | None = None
