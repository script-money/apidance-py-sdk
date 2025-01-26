import json
from apidance.utils import parse_markdown_to_richtext


def load_test_data():
    """Load test data from json file"""
    with open("./tests/test_rich.json", "r") as f:
        data = json.load(f)
    return data


def test_parse_markdown_to_richtext():
    """Test markdown to richtext parsing with real-world examples"""
    test_cases = [
        (
            """This is a test tweet to check the length, formatting, and overall look of a longer tweet. I want to see how it appears on different devices and if there are any unexpected line breaks or display issues.

I'm also testing the use of hashtags and mentions. Will they work correctly and improve *discoverability*? Let's find out! #TestTweet @YourAccount

This tweet includes a question to encourage engagement. Are people more likely to respond or interact with a longer tweet that asks a question?

Finally, I'm adding a few more sentences to reach the desired word count and see how the tweet handles a variety of sentence lengths and structures. What do you think of **longer-form content** on Twitter? Does it have a place? Let me know your thoughts! Testing, testing, 1, 2, 3! Just a few more words now. This is the end.""",
            [
                {"from_index": 292, "to_index": 307, "richtext_types": ["Italic"]},
                {"from_index": 665, "to_index": 684, "richtext_types": ["Bold"]},
            ],
        ),
    ]

    for markdown_text, expected_tags in test_cases:
        plain_text, actual_tags = parse_markdown_to_richtext(markdown_text)

        # Sort both lists to ensure consistent comparison
        expected_tags = sorted(
            expected_tags,
            key=lambda x: (
                x["from_index"],
                x["to_index"],
                tuple(sorted(x["richtext_types"])),
            ),
        )
        actual_tags = sorted(
            actual_tags,
            key=lambda x: (
                x["from_index"],
                x["to_index"],
                tuple(sorted(x["richtext_types"])),
            ),
        )

        assert len(actual_tags) == len(
            expected_tags
        ), f"Expected {len(expected_tags)} tags, got {len(actual_tags)} for text: {markdown_text}"

        for actual, expected in zip(actual_tags, expected_tags):
            assert actual == expected, f"Expected {expected}, got {actual}"


def test_edge_cases():
    """Test edge cases for markdown parsing"""
    test_cases = [
        #
        (
            "This is *italic* **bold**",
            [
                {"from_index": 8, "to_index": 14, "richtext_types": ["Italic"]},
                {"from_index": 15, "to_index": 19, "richtext_types": ["Bold"]},
            ],
        ),
        #
        (
            "This is a dis*cover*ability test",
            [
                {"from_index": 13, "to_index": 18, "richtext_types": ["Italic"]},
            ],
        ),
    ]

    for markdown_text, expected_tags in test_cases:
        plain_text, actual_tags = parse_markdown_to_richtext(markdown_text)

        # Sort both lists to ensure consistent comparison
        expected_tags = sorted(
            expected_tags,
            key=lambda x: (
                x["from_index"],
                x["to_index"],
                tuple(sorted(x["richtext_types"])),
            ),
        )
        actual_tags = sorted(
            actual_tags,
            key=lambda x: (
                x["from_index"],
                x["to_index"],
                tuple(sorted(x["richtext_types"])),
            ),
        )

        assert len(actual_tags) == len(
            expected_tags
        ), f"Expected {len(expected_tags)} tags, got {len(actual_tags)} for text: {markdown_text}"

        for actual, expected in zip(actual_tags, expected_tags):
            assert actual == expected, f"Expected {expected}, got {actual}"
