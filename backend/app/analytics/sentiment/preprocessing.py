"""Twitter sentiment text preprocessing.

Implements PROJECT_CONTEXT.md §24.2 rules for the XLM-RoBERTa pipeline:
- replace @mentions with @user
- replace URLs with http
- preserve hashtags, emojis, negation, Hindi/Hinglish
- do not modify original tweet text (done at the call site)
"""

import re


def preprocess_tweet(text: str) -> str:
    """Preprocesses a tweet for sentiment inference.

    Args:
        text: The original raw tweet text.

    Returns:
        The preprocessed string.
    """
    if not text:
        return ""

    # Replace mentions with @user
    # Match @ followed by valid Twitter username characters
    text = re.sub(r"@\w+", "@user", text)

    # Replace URLs with http
    text = re.sub(r"http\S+", "http", text)
    
    # Do not strip punctuation or lowercase entirely, the model is cased
    # and relies on punctuation/emojis for sentiment.
    # Just normalize whitespace.
    text = " ".join(text.split())

    return text
