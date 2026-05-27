"""
Peanut 3.0 - Kafka Topic Definitions
"""


class KafkaTopics:
    CHAT_MESSAGE_SENT = "peanut.chat.message.sent"
    LLM_RESPONSE_GENERATED = "peanut.llm.response.generated"
    ANALYTICS_EVENT = "peanut.analytics.event"
    MEMORY_CREATED = "peanut.memory.created"
    MEMORY_CONSOLIDATED = "peanut.memory.consolidated"
    SESSION_CREATED = "peanut.session.created"
    USER_REGISTERED = "peanut.user.registered"
