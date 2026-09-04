"""Tests for sentiment preprocessing."""

from app.analytics.sentiment.preprocessing import preprocess_tweet


def test_preprocess_tweet_mentions():
    text = "@john_doe hello @Jane_Doe!"
    expected = "@user hello @user!"
    assert preprocess_tweet(text) == expected


def test_preprocess_tweet_urls():
    text = "Check this out: https://example.com/test and http://foo.bar"
    expected = "Check this out: http and http"
    assert preprocess_tweet(text) == expected


def test_preprocess_tweet_mixed_and_preservation():
    text = "@somebody This is great! 😂 #awesome https://foo.bar isn't it?"
    # Should replace mention and URL, but keep emoji, hashtags, negation, punctuation
    expected = "@user This is great! 😂 #awesome http isn't it?"
    assert preprocess_tweet(text) == expected


def test_preprocess_tweet_whitespace():
    text = "  Too   much \n whitespace\t\n"
    expected = "Too much whitespace"
    assert preprocess_tweet(text) == expected


def test_preprocess_tweet_empty():
    assert preprocess_tweet("") == ""
    assert preprocess_tweet(None) == ""
