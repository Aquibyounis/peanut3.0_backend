"""
Peanut 3.0 - QStash Topic Definitions

Drop-in replacement for KafkaTopics.
Topic strings are used as URL path segments for QStash webhook routing.
"""


class QStashTopics:
    CHAT_MESSAGE_SENT = "peanut.chat.message.sent"
    LLM_RESPONSE_GENERATED = "peanut.llm.response.generated"
    ANALYTICS_EVENT = "peanut.analytics.event"
    MEMORY_CREATED = "peanut.memory.created"
    MEMORY_CONSOLIDATED = "peanut.memory.consolidated"
    SESSION_CREATED = "peanut.session.created"
    USER_REGISTERED = "peanut.user.registered"

    # Map topics to webhook endpoint paths
    TOPIC_TO_WEBHOOK = {
        CHAT_MESSAGE_SENT: "/webhooks/analytics",
        LLM_RESPONSE_GENERATED: "/webhooks/analytics",
        ANALYTICS_EVENT: "/webhooks/analytics",
        MEMORY_CREATED: "/webhooks/memory",
        MEMORY_CONSOLIDATED: "/webhooks/memory",
    }
