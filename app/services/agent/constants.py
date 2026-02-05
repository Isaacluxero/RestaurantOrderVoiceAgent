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
# NOTE: Keep these specific to avoid false positives
REVISION_INDICATORS = [
    "change",
    "remove",
    "delete",
    "don't want",
    "cancel",
    "take out",
    "take off",
    "no wait",
    "hold on",
    "actually no",
    "remove the",
    "take away",
]

# Indicators that customer is confirming the order
# NOTE: In REVIEW stage, these should be treated carefully to avoid false positives
# The LLM intent should be the primary signal, keywords are secondary validation
CONFIRMATION_INDICATORS = [
    "yes that's",
    "yes correct",
    "yes it is",
    "that's right",
    "that's correct",
    "sounds good",
    "looks good",
    "correct",
    "perfect",
]

# Indicators for "no" response (declining notes/customizations)
NO_RESPONSE_INDICATORS = [
    "no",
    "none",
    "nothing",
    "no thanks",
    "that's fine",
]

