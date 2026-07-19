from collections import defaultdict, deque

from .models import ChatMessage


class ChatContext:

    def __init__(self):
        self.history = defaultdict(
            lambda: deque(maxlen=30)
        )
        self.message_counter = {}

    def increment_counter(self, chat_id: int):
        self.message_counter[chat_id] = (
                self.message_counter.get(chat_id, 0) + 1
        )

        return self.message_counter[chat_id]

    def reset_counter(self, chat_id: int):
        self.message_counter[chat_id] = 0

    def add(
        self,
        chat_id: int,
        message: ChatMessage
    ):
        self.history[chat_id].append(message)


    def get(
        self,
        chat_id: int
    ):
        return list(
            self.history[chat_id]
        )


chat_context = ChatContext()