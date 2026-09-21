"""Shared Discord embed presentation contract."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from formatters.base import BaseFormatter
from version import VERSION


_COMPONENTS_V2_RENDERING = ContextVar(
    "discord_components_v2_rendering",
    default=False,
)


@dataclass(frozen=True)
class DiscordFact:
    """One icon-labelled integration-specific Discord field."""

    icon: str
    label: str
    value: Any
    inline: bool = True


@dataclass(frozen=True)
class DiscordCardData:
    """Normalized data consumed by the shared Discord renderer."""

    source: str
    integration: str
    device: str
    event: str
    message: str
    status: str = "information"
    state: str = ""
    severity: str = ""
    category: str = ""
    source_area: str = ""
    event_time: Any = ""
    device_icon: str = "🖥️"
    source_area_icon: str = "📍"
    event_icon: str = "🔔"
    details: tuple[DiscordFact, ...] = ()
    url: str = ""
    notification: Any = None


class DiscordCardFormatter(BaseFormatter):
    """Render normalized integration data using one bounded Discord embed."""

    EMBED_TEXT_BUDGET = 5900
    MAX_FIELDS = 25
    ESSENTIAL_FIELDS = 3
    # Discord renders embed content more narrowly when a thumbnail is
    # present. Keep the shared rule inside that narrowest width so it never
    # wraps into a second fragment.
    SEPARATOR = "───────────────────────────────────────────────"

    COMPONENTS_V2_FLAG = 1 << 15
    COMPONENT_TYPE_SECTION = 9
    COMPONENT_TYPE_TEXT_DISPLAY = 10
    COMPONENT_TYPE_THUMBNAIL = 11
    COMPONENT_TYPE_SEPARATOR = 14
    COMPONENT_TYPE_CONTAINER = 17

    def format_components_v2(self, notification) -> dict[str, Any]:
        """Render an existing integration through the responsive contract.

        Formatters continue to expose their legacy ``format`` method for
        compatibility and focused unit tests.  Delivery opts into Components
        V2 through this context-local switch, avoiding shared mutable state
        when multiple notifications are formatted concurrently.
        """

        token = _COMPONENTS_V2_RENDERING.set(True)
        try:
            return self.format(notification)
        finally:
            _COMPONENTS_V2_RENDERING.reset(token)

    def _render_discord_card(self, data: DiscordCardData) -> dict[str, Any]:
        if _COMPONENTS_V2_RENDERING.get():
            return self._render_discord_components_v2(data)

        status_icon, color, default_state = self._discord_status(
            data.status,
            data.severity,
        )
        state = self._label(data.state) or default_state
        severity = self._label(data.severity) or default_state
        category = self._label(data.category) or "Event"
        source_area = self._truncate(
            self._label(data.source_area) or category,
            700,
        )
        device = self._truncate(data.device or data.integration, 120)
        event = self._truncate(data.event or "Notification", 180)
        message = self._truncate(data.message or event, 1024)
        event_time = self._format_datetime(data.event_time)

        fields = [
            self._discord_field(status_icon, "Severity", severity),
            self._discord_field(
                self._category_icon(data.category),
                "Category",
                category,
            ),
        ]
        if event_time:
            fields.append(
                self._discord_field("🕒", "Event time", event_time)
            )

        embed: dict[str, Any] = {
            "title": self._truncate(
                f"{data.device_icon} {status_icon} {device} • {event}",
                256,
            ),
            "description": self._truncate(
                f"{data.integration} • {status_icon} **{state}** • "
                f"{data.source_area_icon} {source_area}\n"
                f"{self.SEPARATOR}\n{self._discord_highlight(message)}",
                2048,
            ),
            "color": color,
            "fields": fields,
            "footer": {"text": f"Theriark • Nowlert v{VERSION}"},
        }

        detail_fields = self._discord_detail_fields(data.details)
        if detail_fields:
            embed["fields"].extend(detail_fields)

        if data.url:
            embed["url"] = self._truncate(data.url, 2000)

        self._set_discord_thumbnail(embed, data.source)
        self._enforce_discord_budget(embed)
        self._finish_discord_footer(embed)
        payload = {"embeds": [embed]}
        if data.notification is None:
            return payload

        # Classic Embed v1 is the formatter contract itself, not an
        # adapter-only post-processing step. Components V2 returns above
        # before this path is reached.
        from formatters.discord_classic_v1 import render_classic_embed_v1

        rendered = self._sanitize_payload(
            render_classic_embed_v1(data.notification, payload)
        )
        embeds = rendered.get("embeds") if isinstance(rendered, dict) else None
        if isinstance(embeds, list) and embeds and isinstance(embeds[0], dict):
            self._enforce_discord_budget(embeds[0])
        return rendered

    def _render_discord_components_v2(
        self,
        data: DiscordCardData,
    ) -> dict[str, Any]:
        """Render one responsive Discord Components V2 card.

        Xen Orchestra keeps the same shared Components V2 shell as the other
        integrations, but uses the approved source-specific backup geometry.
        """

        is_xo = data.source == "xo" and data.notification is not None
        status_icon, color, default_state = self._discord_status(
            data.status,
            data.severity,
        )
        if is_xo:
            status_icon, color, default_state = self._discord_xo_status(
                data.notification
            )

        state = self._label(data.state) or default_state
        severity = self._label(data.severity) or default_state
        category = self._label(data.category) or "Event"
        source_area = self._truncate(
            self._label(data.source_area) or category,
            280,
        )
        device = self._truncate(data.device or data.integration, 120)
        event = self._truncate(data.event or "Notification", 180)
        message = self._truncate(data.message or event, 1000)
        event_time = self._format_datetime(data.event_time)

        if is_xo:
            notification = data.notification
            source_area = self._truncate(
                str(notification.repository or data.source_area or "Backup").strip(),
                280,
            )
            device = self._truncate(
                notification.job_name
                or notification.title
                or notification.subject
                or data.device
                or "Xen Orchestra backup",
                180,
            )
            event = self._truncate(data.event or default_state, 180)
            message = self._truncate(
                notification.subject
                or notification.body
                or data.message
                or f"Backup report for {device}",
                1000,
            )
            event_time = self._discord_xo_time(
                notification.end_time or notification.start_time
            )
            title_text = "### 🗄️ Xen Orchestra"
            context_text = f"-# {source_area}"
            xo_status_text = (
                f"### {status_icon} {event}\n"
                f"-# {device}"
            )
        else:
            title_text = (
                f"### {data.device_icon} {status_icon} {device} • {event}"
            )
            context_text = (
                f"-# {data.integration} • {status_icon} **{state}** • "
                f"{data.source_area_icon} {source_area}"
            )

        icon_url = self._discord_product_icon_url(data.source)
        if icon_url:
            header = {
                "type": self.COMPONENT_TYPE_SECTION,
                "components": (
                    [
                        self._discord_v2_text(title_text),
                        self._discord_v2_text(context_text),
                        self._discord_v2_text(xo_status_text),
                    ]
                    if is_xo
                    else [
                        self._discord_v2_text(title_text),
                        self._discord_v2_text(context_text),
                    ]
                ),
                "accessory": {
                    "type": self.COMPONENT_TYPE_THUMBNAIL,
                    "media": {"url": icon_url},
                    "description": f"{data.integration} logo",
                },
            }
            context_components = []
        else:
            header = self._discord_v2_text(title_text)
            context_components = [self._discord_v2_text(context_text)]

        metrics = [
            f"{status_icon} **Severity:** {severity}",
            (
                f"{self._category_icon(data.category)} "
                f"**Category:** {category}"
            ),
        ]
        if event_time:
            metrics.append(f"🕒 **Event time:** {event_time}")

        children = [
            header,
            *context_components,
            self._discord_v2_separator(),
            self._discord_v2_text(self._discord_highlight(message)),
            self._discord_v2_separator(divider=False),
            self._discord_v2_text("  •  ".join(metrics)),
        ]

        if is_xo:
            details = self._discord_v2_xo_details(
                data.notification,
                data.details,
            )
        else:
            generic_details = self._discord_v2_details(data.details)
            details = (
                f"**📋 Event details**\n{generic_details}"
                if generic_details
                else ""
            )

        if details:
            children.extend((
                self._discord_v2_separator(),
                self._discord_v2_text(details),
            ))

        if is_xo:
            vm_layout = self._discord_v2_xo_vm_layout(data.notification)
            if vm_layout:
                children.extend((
                    self._discord_v2_separator(divider=False),
                    self._discord_v2_text(vm_layout),
                ))

        footer = f"-# Theriark • Nowlert v{VERSION}"
        if is_xo:
            footer = (
                f"-# Theriark - Nowlert v{VERSION}  ·  "
                "Xen Orchestra Notification"
            )

        children.extend((
            self._discord_v2_separator(),
            self._discord_v2_text(footer),
        ))

        return {
            "flags": self.COMPONENTS_V2_FLAG,
            "components": [
                {
                    "type": self.COMPONENT_TYPE_CONTAINER,
                    "accent_color": color,
                    "components": children,
                }
            ],
        }

    @staticmethod
    def _discord_xo_status(notification) -> tuple[str, int, str]:
        """Return the approved success/failure/skipped XO lifecycle."""

        value = str(getattr(notification, "status", "") or "").strip().casefold()
        failed = int(getattr(notification, "vm_failed", 0) or 0)
        skipped = int(getattr(notification, "vm_skipped", 0) or 0)

        if value in {"failure", "failed", "error", "critical"} or failed:
            return "🚨", 0xED4245, "Failure"
        if value in {"skipped", "warning"} or skipped:
            return "ℹ️", 0x3498DB, "Skipped"
        return "✅", 0x57F287, "Success"

    def _discord_xo_time(self, value: Any) -> str:
        """Keep XO's source UTC timestamp presentation used by the approved card."""

        if not self._meaningful_fact(value):
            return ""
        return self._truncate(str(value).strip(), 120)

    def _discord_v2_xo_details(
        self,
        notification,
        details: tuple[DiscordFact, ...],
    ) -> str:
        """Render the approved two-column XO operator panel."""

        facts = {
            str(fact.label): fact.value
            for fact in details
            if self._meaningful_fact(fact.value)
        }
        left = (
            ("🧰 Mode", getattr(notification, "mode", "")),
            ("⏱ Duration", facts.get("Duration", "")),
            ("📦 Transfer size", getattr(notification, "transfer_size", "")),
            ("🚀 Speed", getattr(notification, "transfer_speed", "")),
        )
        right = (
            ("💾 Repository", getattr(notification, "repository", "")),
            (
                "▶ Started",
                self._discord_xo_time(getattr(notification, "start_time", "")),
            ),
            (
                "🏁 Finished",
                self._discord_xo_time(getattr(notification, "end_time", "")),
            ),
            ("📊 Result", facts.get("Result", "")),
        )

        lines = []
        for (left_label, left_value), (right_label, right_value) in zip(
            left,
            right,
        ):
            left_text = self._discord_xo_grid_fact(left_label, left_value)
            right_text = self._discord_xo_grid_fact(right_label, right_value)
            if left_text and right_text:
                lines.append(f"{left_text:<34}{right_text}")
            elif left_text:
                lines.append(left_text)
            elif right_text:
                lines.append(right_text)

        for label in ("Run ID", "Job ID"):
            value = facts.get(label, "")
            if self._meaningful_fact(value):
                lines.append(
                    self._discord_xo_grid_fact(f"🆔 {label}", value)
                )

        if not lines:
            return ""
        return (
            "**📋 Event details**\n"
            + self._discord_xo_code_panel(lines)
        )

    def _discord_v2_xo_vm_layout(self, notification) -> str:
        """Render XO VM outcomes as compact grid panels matching the approved card."""

        successful = self._discord_xo_vm_entries(
            notification,
            getattr(notification, "successful_vms", []),
            include_reason=False,
        )
        failed = self._discord_xo_vm_entries(
            notification,
            getattr(notification, "failed_vms", []),
            include_reason=True,
        )
        skipped = self._discord_xo_vm_entries(
            notification,
            getattr(notification, "skipped_vms", []),
            include_reason=True,
        )

        blocks = []
        if successful and failed:
            blocks.append(
                self._discord_xo_two_group_panel(
                    "✅ SUCCESSFUL VMS",
                    successful,
                    "❌ FAILED VM" if len(failed) == 1 else "❌ FAILED VMS",
                    failed,
                )
            )
            successful = []
            failed = []
        elif successful and skipped:
            blocks.append(
                self._discord_xo_two_group_panel(
                    "✅ SUCCESSFUL VMS",
                    successful,
                    "⚠ SKIPPED VM" if len(skipped) == 1 else "⚠ SKIPPED VMS",
                    skipped,
                )
            )
            successful = []
            skipped = []

        if successful:
            blocks.append(self._discord_xo_success_grid(successful))
        if failed:
            blocks.append(
                self._discord_xo_single_group_panel(
                    "❌ FAILED VM" if len(failed) == 1 else "❌ FAILED VMS",
                    failed,
                )
            )
        if skipped:
            blocks.append(
                self._discord_xo_single_group_panel(
                    "⚠ SKIPPED VM" if len(skipped) == 1 else "⚠ SKIPPED VMS",
                    skipped,
                )
            )

        return "\n".join(block for block in blocks if block)

    def _discord_xo_vm_entries(
        self,
        notification,
        values,
        *,
        include_reason: bool,
    ) -> list[tuple[str, str, str]]:
        """Return bounded VM name/transfer/reason rows without changing source data."""

        if not isinstance(values, list):
            return []

        details = getattr(notification, "vm_details", {}) or {}
        entries = []
        for raw_name in values[:10]:
            name = self._discord_xo_cell(raw_name, 90)
            if not name:
                continue
            detail = details.get(raw_name, {})
            if not isinstance(detail, dict):
                detail = {}

            transfer = []
            if self._meaningful_fact(detail.get("size")):
                transfer.append(
                    f"📦 {self._discord_xo_cell(detail.get('size'), 60)}"
                )
            if self._meaningful_fact(detail.get("speed")):
                transfer.append(
                    f"🚀 {self._discord_xo_cell(detail.get('speed'), 60)}"
                )
            repository = detail.get("repository")
            if (
                self._meaningful_fact(repository)
                and repository != getattr(notification, "repository", "")
            ):
                transfer.append(
                    f"💾 {self._discord_xo_cell(repository, 90)}"
                )

            reason = ""
            if include_reason and self._meaningful_fact(detail.get("error")):
                reason = self._discord_xo_cell(detail.get("error"), 300)

            entries.append((name, " • ".join(transfer), reason))
        return entries

    def _discord_xo_success_grid(
        self,
        entries: list[tuple[str, str, str]],
    ) -> str:
        """Render up to three successful VMs per row like the approved mockup."""

        lines = [f"✅ SUCCESSFUL VMS ({len(entries)})"]
        width = 27
        for offset in range(0, len(entries), 3):
            row = entries[offset : offset + 3]
            names = [f"✅ {name}" for name, _facts, _reason in row]
            facts = [facts or "—" for _name, facts, _reason in row]
            lines.append(
                "".join(f"{value:<{width}}" for value in names).rstrip()
            )
            lines.append(
                "".join(f"{value:<{width}}" for value in facts).rstrip()
            )
        return self._discord_xo_code_panel(lines)

    def _discord_xo_two_group_panel(
        self,
        left_title: str,
        left_entries: list[tuple[str, str, str]],
        right_title: str,
        right_entries: list[tuple[str, str, str]],
    ) -> str:
        """Render success and failed/skipped groups as two visual columns."""

        width = 39
        left_heading = f"{left_title} ({len(left_entries)})"
        right_heading = f"{right_title} ({len(right_entries)})"
        lines = [f"{left_heading:<{width}}{right_heading}".rstrip()]
        rows = max(len(left_entries), len(right_entries))
        reasons = []
        for index in range(rows):
            left = (
                left_entries[index]
                if index < len(left_entries)
                else ("", "", "")
            )
            right = (
                right_entries[index]
                if index < len(right_entries)
                else ("", "", "")
            )

            left_name = f"✅ {left[0]}" if left[0] else ""
            right_icon = "❌" if right_title.startswith("❌") else "⚠"
            right_name = f"{right_icon} {right[0]}" if right[0] else ""
            lines.append(f"{left_name:<{width}}{right_name}".rstrip())

            left_facts = left[1] or ""
            right_facts = right[1] or ""
            if left_facts or right_facts:
                lines.append(
                    f"{left_facts:<{width}}{right_facts}".rstrip()
                )
            if right[2]:
                reasons.append(f"↳ {right_icon} {right[2]}")

        lines.extend(reasons)
        return self._discord_xo_code_panel(lines)

    def _discord_xo_single_group_panel(
        self,
        title: str,
        entries: list[tuple[str, str, str]],
    ) -> str:
        """Render one failed/skipped group when no paired success group exists."""

        icon = "❌" if title.startswith("❌") else "⚠"
        lines = [f"{title} ({len(entries)})"]
        for name, facts, reason in entries:
            lines.append(f"{icon} {name}")
            if facts:
                lines.append(facts)
            if reason:
                lines.append(f"↳ {icon} {reason}")
        return self._discord_xo_code_panel(lines)

    def _discord_xo_grid_fact(self, label: str, value) -> str:
        """Format one compact key/value item used by the XO details grid."""

        if not self._meaningful_fact(value):
            return ""
        safe_label = self._discord_xo_cell(label, 32)
        safe_value = self._discord_xo_cell(value, 340)
        return f"{safe_label}: {safe_value}"

    def _discord_xo_cell(self, value, limit: int) -> str:
        """Flatten one value so source text cannot break the grid/code fence."""

        text = self._sanitize_text(value).replace("\r", " ").replace("\n", " ")
        text = " ".join(text.split()).replace(chr(96) * 3, "'''")
        return self._truncate(text, limit)

    def _discord_xo_code_panel(self, lines: list[str]) -> str:
        """Wrap one visual panel while always retaining the closing code fence."""

        content = "\n".join(line.rstrip() for line in lines if line).strip()
        content = content.replace(chr(96) * 3, "'''")
        if len(content) > 1740:
            content = self._truncate(content, 1739).rstrip() + "…"
        fence = chr(96) * 3
        return f"{fence}text\n{content or '—'}\n{fence}"

    def _discord_v2_details(
        self,
        details: tuple[DiscordFact, ...],
    ) -> str:
        """Return a compact, bounded vertical detail list."""

        entries = []
        for fact in details:
            if not self._meaningful_fact(fact.value):
                continue
            label = self._truncate(fact.label, 120)
            value = self._truncate(fact.value, 700)
            entries.append(f"{fact.icon} **{label}:** {value}")
        return self._truncate("\n".join(entries), 1800)

    def _discord_v2_text(self, content: Any) -> dict[str, Any]:
        """Build a Text Display without allowing source text to ping users."""

        safe = self._truncate(content, 2000).replace("@", "@\u200b")
        return {
            "type": self.COMPONENT_TYPE_TEXT_DISPLAY,
            "content": safe or "—",
        }

    def _discord_v2_separator(
        self,
        *,
        divider: bool = True,
        spacing: int = 1,
    ) -> dict[str, Any]:
        """Build a native divider that follows the rendered card width."""

        return {
            "type": self.COMPONENT_TYPE_SEPARATOR,
            "divider": divider,
            "spacing": 2 if spacing == 2 else 1,
        }

    def _discord_highlight(self, value: Any) -> str:
        """Render the event message as a full-width Discord code block."""

        text = self._truncate(value, 1014).replace("```", "'''")
        return f"```\n{text or '—'}\n```"

    def _finish_discord_footer(self, embed: dict[str, Any]) -> None:
        """Place one full-width rule immediately above the footer."""

        fields = embed.get("fields", [])
        if not fields:
            return
        last = fields[-1]
        if str(last.get("value") or "").endswith(self.SEPARATOR):
            self._trim_discord_description_for_budget(embed)
            return
        if last.get("name") == "\u200b" and not last.get(
            "inline",
            True,
        ):
            value = str(last.get("value") or "").rstrip()
            maximum = 1024 - len(self.SEPARATOR) - 1
            last["value"] = (
                f"{self._truncate(value, maximum).rstrip()}\n{self.SEPARATOR}"
            )
        elif len(fields) < self.MAX_FIELDS:
            fields.append(self._discord_separator())
        self._trim_discord_description_for_budget(embed)

    def _trim_discord_description_for_budget(
        self,
        embed: dict[str, Any],
    ) -> None:
        """Keep the mandatory rules without exceeding Discord's text limit."""

        excess = self._discord_text_size(embed) - self.EMBED_TEXT_BUDGET
        if excess <= 0:
            return
        description = str(embed.get("description") or "")
        marker = f"\n{self.SEPARATOR}\n```\n"
        suffix = "\n```"
        if marker in description and description.endswith(suffix):
            context, message = description.split(marker, 1)
            message = message[: -len(suffix)]
            maximum = max(len(message) - excess, 1)
            embed["description"] = (
                f"{context}{marker}{self._truncate(message, maximum)}{suffix}"
            )
            return
        embed["description"] = self._truncate(
            description,
            max(len(description) - excess, 1),
        )

    def _discord_detail_fields(
        self,
        details: tuple[DiscordFact, ...],
    ) -> list[dict[str, Any]]:
        """Group integration-specific details into readable vertical lists."""

        entries: list[str] = []
        for fact in details:
            if not self._meaningful_fact(fact.value):
                continue
            label = self._truncate(fact.label, 120)
            value = self._truncate(fact.value, 880)
            if "\n" in value:
                entries.append(f"{fact.icon} **{label}:**\n{value}")
            else:
                entries.append(f"{fact.icon} **{label}:** {value}")

        if not entries:
            return []

        chunks: list[str] = []
        current = ""
        for entry in entries:
            candidate = f"{current}\n{entry}" if current else entry
            if len(candidate) <= 880:
                current = candidate
                continue
            if current:
                chunks.append(current)
            current = self._truncate(entry, 880)
        if current:
            chunks.append(current)

        fields = []
        for index, chunk in enumerate(chunks):
            if index == 0:
                chunk = (
                    f"{self.SEPARATOR}\n"
                    f"📋 **Event details**\n{chunk}"
                )
            fields.append({
                "name": "\u200b",
                "value": chunk,
                "inline": False,
            })
        return fields

    def _discord_separator(self) -> dict[str, Any]:
        return {
            "name": "\u200b",
            "value": self.SEPARATOR,
            "inline": False,
        }

    def _discord_field(
        self,
        icon: str,
        label: str,
        value: Any,
        inline: bool = True,
    ) -> dict[str, Any]:
        name = f"{icon} {label}".strip() or "\u200b"
        return {
            "name": self._truncate(name, 256),
            "value": self._truncate(value, 1024) or "—",
            "inline": inline,
        }

    def _enforce_discord_budget(self, embed: dict[str, Any]) -> None:
        fields = embed.get("fields", [])
        del fields[self.MAX_FIELDS :]

        # Integration-specific fields are ordered by importance. Preserve the
        # Severity/Category/Event time row and remove optional details from
        # the end first.
        essential_fields = min(
            self.ESSENTIAL_FIELDS,
            sum(bool(field.get("inline")) for field in fields),
        )
        while (
            len(fields) > essential_fields
            and self._discord_text_size(embed) > self.EMBED_TEXT_BUDGET
        ):
            fields.pop()

        if self._discord_text_size(embed) <= self.EMBED_TEXT_BUDGET:
            return

        excess = self._discord_text_size(embed) - self.EMBED_TEXT_BUDGET
        description = str(embed.get("description", ""))
        embed["description"] = self._truncate(
            description,
            max(len(description) - excess, 1),
        )

    @staticmethod
    def _discord_text_size(embed: dict[str, Any]) -> int:
        size = len(str(embed.get("title", "")))
        size += len(str(embed.get("description", "")))
        size += len(str(embed.get("footer", {}).get("text", "")))
        for field in embed.get("fields", []):
            size += len(str(field.get("name", "")))
            size += len(str(field.get("value", "")))
        return size

    # Compatibility for existing formatter limit tests and integrations that
    # inspected the former product-specific helpers.
    def _embed_text_size(self, embed: dict[str, Any]) -> int:
        return self._discord_text_size(embed)

    @staticmethod
    def _discord_status(status: Any, severity: Any = "") -> tuple[str, int, str]:
        status_value = str(status or "").strip().casefold()
        severity_value = str(severity or "").strip().casefold()
        resolved = {
            "cleared", "normal", "ok", "recovered", "resolved", "success",
            "successful",
        }
        critical = {
            "critical", "danger", "disaster", "emergency", "error",
            "failed", "failure", "high",
        }
        warning = {
            "alert", "average", "caution", "degraded", "medium", "warn",
            "warning",
        }

        # Current state wins over historical severity on recovery cards.
        if status_value in resolved:
            return "✅", 0x2ECC71, "Resolved"
        if status_value in critical:
            return "🚨", 0xE74C3C, "Critical"
        if status_value in warning:
            return "⚠️", 0xF39C12, "Warning"
        if severity_value in critical:
            return "🚨", 0xE74C3C, "Critical"
        if severity_value in warning:
            return "⚠️", 0xF39C12, "Warning"
        if severity_value in resolved:
            return "✅", 0x2ECC71, "Resolved"
        return "ℹ️", 0x3498DB, "Information"

    @staticmethod
    def _category_icon(category: Any) -> str:
        value = str(category or "").strip().casefold()
        rules = (
            (("storage", "disk", "raid", "volume"), "💾"),
            (("security", "auth", "login"), "🛡️"),
            (("backup", "replication", "sync"), "🔄"),
            (("power", "ups", "battery"), "🔌"),
            (("network", "wifi", "ethernet"), "🌐"),
            (("update", "firmware"), "⬆️"),
            (("thermal", "temperature", "fan"), "🌡️"),
            (("memory", "dimm", "ecc"), "🧠"),
            (("system", "hardware"), "⚙️"),
        )
        for terms, icon in rules:
            if any(term in value for term in terms):
                return icon
        return "📁"

    @staticmethod
    def _label(value: Any) -> str:
        text = str(value or "").replace("_", " ").strip()
        if not text:
            return ""

        def label_token(token: str) -> str:
            parts = token.split("-")
            return "-".join(
                part
                if part.isupper() or any(character.isdigit() for character in part)
                else part.capitalize()
                for part in parts
            )

        return " ".join(label_token(token) for token in text.split())

    def _meaningful_fact(self, value: Any) -> bool:
        if value is None:
            return False
        text = self._sanitize_text(value).strip()
        return text.casefold() not in {"", "-", "—", "n/a", "none", "null"}
