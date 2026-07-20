import asyncio

from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError
from openai import RateLimitError

from .models import Member, ChatMessage
from .chat_info import (
    bot_about, chat_about,
    chat_members, mission,
    rules, style
)

class PromptBuilder:

    def __init__(
        self,
        bot_about: str,
        chat_about: str,
        chat_members: list[Member],
        mission: str,
        rules: str,
        style: str
    ):
        self.bot_about = bot_about
        self.chat_about = chat_about
        self.chat_members = chat_members
        self.mission = mission
        self.rules = rules
        self.style = style
        self.str_members = self._members_to_str()


    def _members_to_str(self) -> str:
        about_members = ""
        for member in self.chat_members:
            about_members += (
                f"Юзернейм: {member.username}\n"
                f"Прозвища: {member.name}\n"
                f"Описание: {member.description}\n"
                f"Твое отношение к нему: {member.relationship}\n\n"
            )
        return about_members

    def _history_to_str(self, messages: list[ChatMessage]) -> str:
        messages_history = ""
        for message in messages:
            messages_history += (
                f"{message.username}"
                f"{' -> ' + message.reply_to_username if message.reply_to_username else ''}:"
                f" {message.text}\n"
            )
        return messages_history


    def build(
        self,
        messages: list[ChatMessage]
    ) -> str:
        prompt = (
            "Ты участвуешь в переписке Telegram чата от лица бота Жоры "
            "Кто ты:\n"
            f"{self.bot_about}\n"
            "Описание чата:\n"
            f"{self.chat_about}\n"
            f"Участники:\n {self.str_members}\n"
            "История сообщений:\n"
            f"{self._history_to_str(messages)}\n"
            "Текущее задание:\n"
            f"{self.mission}\n"
            "Правила поведения:\n"
            f"{self.rules}\n"
            "Стиль общения:\n"
            f"{self.style}\n"
            "Ограничения:\n"
            "Верни JSON\n"
            "Никаких пояснений, комментариев или оформления.\n"
            "Текст обычно не более 20 слов, кроме случаев, "
            "когда участник просит объяснение, инструкцию или подробный ответ."
            
            'КРИТИЧЕСКИ ВАЖНО: '
            'Ответ должен состоять ТОЛЬКО из одного валидного JSON объекта. '
            'Нельзя писать текст до JSON. '
            'Нельзя писать текст после JSON. '
            'Нельзя использовать markdown. '
            'Нельзя использовать ```json. '
            'JSON обязан быть завершен всеми закрывающими скобками. '
            'Если action="reply", весь текст ответа должен находиться только внутри поля text.'
            )

        return prompt


import asyncio
import httpx
from google import genai
class LLMService:

    def __init__(self, api_key: str):
        self.client = genai.Client(
            api_key=api_key
        ).aio

    async def generate(
        self,
        prompt: str
    ) -> str:

        for attempt in range(3):

            try:
                response = await self.client.models.generate_content(
                    model="gemini-3.1-flash-lite",
                    contents=prompt,
                    config={
                        "temperature": 1.2,
                        "max_output_tokens": 500,
                    }
                )

                if not response.text:
                    raise RuntimeError(
                        f"Gemini returned empty response: {response}"
                    )

                return response.text.strip()


            except (ServerError, ClientError) as e:

                if attempt == 2:
                    raise

                await asyncio.sleep(
                    2 ** attempt
                )

import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("GEMINI_API_KEY")
llm_service = LLMService(TOKEN)

prompt_builder = PromptBuilder(
    bot_about=bot_about,
    chat_about=chat_about,
    chat_members=chat_members,
    mission=mission,
    rules=rules,
    style=style,
)