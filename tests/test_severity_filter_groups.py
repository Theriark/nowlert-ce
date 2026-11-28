"""The Delivery history severity groups follow the notification card buckets."""

from __future__ import annotations

import pytest

from formatters.discord_common import DiscordCardFormatter
from storage.delivery import SEVERITY_FILTER_GROUPS, severity_filter_group


CARD_LABELS = {
    "critical": "Critical",
    "warning": "Warning",
    "resolved": "Resolved",
    "information": "Information",
}


@pytest.mark.parametrize(
    "group, word",
    [(group, word) for group, words in SEVERITY_FILTER_GROUPS.items() for word in words],
)
def test_every_grouped_word_gets_its_group_bucket_on_the_cards(group, word):
    # The filter groups were copied by hand from DiscordCardFormatter's
    # buckets; a word added to one list but not the other fails here.
    _icon, _colour, label = DiscordCardFormatter._discord_status("", word)

    assert label == CARD_LABELS[group]
    assert severity_filter_group(word) == group
    assert severity_filter_group(word.upper()) == group


def test_words_outside_the_groups_stay_separate():
    assert severity_filter_group("Debug") == "debug"
    assert severity_filter_group(" notice ") == "notice"
    assert severity_filter_group("") == ""
