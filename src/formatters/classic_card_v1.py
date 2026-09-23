"""Destination-neutral Classic Card v1 conversion helpers."""

from __future__ import annotations

from formatters.discord_classic_v1 import render_classic_embed_v1


def classic_card_v1_from_discord_payload(
    payload: dict,
    *,
    rich: bool = False,
) -> dict:
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

    normalized_fields = [
        {
            "title": str(field.get("name") or ""),
            "value": str(field.get("value") or ""),
            "inline": bool(field.get("inline", False)),
        }
        for field in fields
        if isinstance(field, dict)
    ]

    color = embed.get("color")
    presentation = {
        "style": "classic_card_v1",
        "title": str(embed.get("title") or ""),
        "description": str(embed.get("description") or ""),
        "color": color,
        "fields": normalized_fields,
    }

    rich_titles = [
        field["title"]
        for field in normalized_fields[:3]
    ]
    is_rich = rich or (
        len(rich_titles) == 3
        and "Severity" in rich_titles[0]
        and "Category" in rich_titles[1]
        and "Event time" in rich_titles[2]
        and any(
            field["title"] == "🧾 Event details"
            for field in normalized_fields
        )
    )
    if is_rich:
        try:
            accent = f"#{int(color) & 0xFFFFFF:06X}"
        except (TypeError, ValueError):
            accent = "#3498DB"
        presentation.update(
            {
                "visual_system": "nowlert_rich_classic_v1",
                "integration": str(embed.get("title") or ""),
                "accent": accent,
                "summary": [
                    {
                        "label": field["title"],
                        "value": field["value"],
                    }
                    for field in normalized_fields
                    if field["inline"]
                ][:3],
                "sections": [
                    {
                        "title": field["title"],
                        "items": [
                            {
                                "title": "",
                                "value": field["value"],
                            }
                        ],
                    }
                    for field in normalized_fields
                    if not field["inline"]
                ],
            }
        )

    footer = embed.get("footer")
    if isinstance(footer, dict) and footer.get("text"):
        presentation["footer"] = str(footer["text"])

    thumbnail = embed.get("thumbnail")
    if (
        is_rich
        and isinstance(thumbnail, dict)
        and thumbnail.get("url")
    ):
        presentation["source_icon"] = str(thumbnail["url"])

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
