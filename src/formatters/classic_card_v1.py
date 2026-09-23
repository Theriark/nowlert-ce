"""Destination-neutral Classic Card v1 conversion helpers."""

from __future__ import annotations

from formatters.discord_classic_v1 import render_classic_embed_v1


def classic_card_v1_from_discord_payload(payload: dict) -> dict:
    """Convert one Discord Classic embed into the neutral Classic Card v1 model."""

    embeds = payload.get("embeds") if isinstance(payload, dict) else None
    if (
        not isinstance(embeds, list)
        or not embeds
        or not isinstance(embeds[0], dict)
    ):
        raise ValueError(
            "Discord Classic preview did not produce a Classic preview embed"
        )

    embed = embeds[0]
    fields = embed.get("fields")
    if not isinstance(fields, list):
        fields = []

    presentation = {
        "style": "classic_card_v1",
        "title": str(embed.get("title") or ""),
        "description": str(embed.get("description") or ""),
        "color": embed.get("color"),
        "fields": [
            {
                "title": str(field.get("name") or ""),
                "value": str(field.get("value") or ""),
                "inline": bool(field.get("inline", False)),
            }
            for field in fields
            if isinstance(field, dict)
        ],
    }

    footer = embed.get("footer")
    if isinstance(footer, dict) and footer.get("text"):
        presentation["footer"] = str(footer["text"])

    for key in ("timestamp", "url"):
        if embed.get(key):
            presentation[key] = embed[key]

    return presentation


def render_classic_card_v1(notification) -> dict:
    """Render approved Classic semantics without binding to a destination."""

    payload = render_classic_embed_v1(
        notification,
        {"embeds": [{}]},
    )
    return classic_card_v1_from_discord_payload(payload)


__all__ = [
    "classic_card_v1_from_discord_payload",
    "render_classic_card_v1",
]
