"""Constants for conversation flow and stage transitions."""

# Indicators that customer is done ordering
DONE_ORDERING_INDICATORS = [
    "that's all",
    "that's it",
    "nothing else",
    "i'm done",
    "i'm finished",
    "that's everything",
    "no that's all",
    "no thanks that's all",
]

# Indicators that customer wants to revise their order
REVISION_INDICATORS = [
    "change",
    "remove",
    "delete",
    "don't want",
    "cancel",
    "take out",
    "add",
    "actually",
    "wait",
    "hold on",
    "no wait",
]

# Indicators that customer is confirming the order
CONFIRMATION_INDICATORS = [
    "yes",
    "correct",
    "that's right",
    "sounds good",
    "perfect",
    "that works",
    "looks good",
    "that's correct",
]

# Indicators for "no" response (declining notes/customizations)
NO_RESPONSE_INDICATORS = [
    "no",
    "none",
    "nothing",
    "no thanks",
    "that's fine",
]

