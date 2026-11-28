"""The Delivery history severity groups follow the notification card buckets."""

from __future__ import annotations

import pytest

from constants.severity import CRITICAL_WORDS, INFORMATION_WORDS, RESOLVED_WORDS, WARNING_WORDS
from formatters.discord_common import DiscordCardFormatter
from formatters.teams_common import TeamsCardFormatter
from storage.delivery import SEVERITY_FILTER_GROUPS, severity_filter_group


CARD_BUCKETS = {
    "critical": ("Critical", CRITICAL_WORDS),
    "warning": ("Warning", WARNING_WORDS),
    "resolved": ("Resolved", RESOLVED_WORDS),
    "information": ("Information", INFORMATION_WORDS),
}


def test_the_filter_groups_are_exactly_the_card_buckets():
    # Both directions: every bucket word is in its group and every group word
    # is in its bucket, and no word is in two groups.
    assert set(SEVERITY_FILTER_GROUPS) == set(CARD_BUCKETS)
    for group, (_label, words) in CARD_BUCKETS.items():
        assert set(SEVERITY_FILTER_GROUPS[group]) == set(words), group
    every_word = [word for words in SEVERITY_FILTER_GROUPS.values() for word in words]
    assert len(every_word) == len(set(every_word))


@pytest.mark.parametrize(
    "group, word",
    [(group, word) for group, words in SEVERITY_FILTER_GROUPS.items() for word in words],
)
def test_every_grouped_word_gets_its_group_bucket_on_the_cards(group, word):
    _icon, _colour, discord_label = DiscordCardFormatter._discord_status("", word)
    _teams_icon, _teams_colour, teams_label = TeamsCardFormatter._teams_status("", word)

    assert discord_label == CARD_BUCKETS[group][0]
    assert teams_label == CARD_BUCKETS[group][0]
    assert severity_filter_group(word) == group
    assert severity_filter_group(word.upper()) == group


def test_words_outside_the_groups_stay_separate():
    assert severity_filter_group("Debug") == "debug"
    assert severity_filter_group(" notice ") == "notice"
    assert severity_filter_group("") == ""
