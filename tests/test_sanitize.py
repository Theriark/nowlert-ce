"""Credential redaction preserves context around complete quoted values."""

import pytest

from formatters.presentation import PresentationMixin
from storage.sanitize import sanitize_text


@pytest.mark.parametrize("sanitize", [sanitize_text, PresentationMixin()._sanitize_text])
@pytest.mark.parametrize("value, expected", [
    ('password="correct horse battery staple" failed', 'password=<redacted> failed'),
    ("token='two words' retry=3", 'token=<redacted> retry=3'),
    ('{"password": "two words", "attempt": 3}', '{"password": <redacted>, "attempt": 3}'),
    (r'password="escaped \"quote\" and tail" retry=3', 'password=<redacted> retry=3'),
    (r"secret='escaped \'quote\' and tail' retry=3", 'secret=<redacted> retry=3'),
    ('password="unclosed secret tail', 'password=<redacted>'),
    ('password="unclosed secret tail\\', 'password=<redacted>'),
    ('password="" retry=3', 'password=<redacted> retry=3'),
    ('password=single retry=3', 'password=<redacted> retry=3'),
    ('password must contain 12 characters; retry=3', 'password must contain 12 characters; retry=3'),
])
def test_quoted_credentials_are_redacted_without_losing_context(sanitize, value, expected):
    assert sanitize(value) == expected
