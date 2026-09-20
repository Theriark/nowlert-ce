"""Bounded Slack presentation for normalized notifications."""

from __future__ import annotations

import re

from formatters.discord_classic_v1 import render_classic_embed_v1
from formatters.presentation import PresentationMixin
from models import Notification
from outputs.platform_common import safe_action_url


CLASSIC_FOOTER = "🦉 Nowlert CE • Classic Card"
_MARKDOWN_LINK = re.compile(r"\[([^\]\n]{1,120})\]\((https://[^)\s]+)\)")


class SlackFormatter(PresentationMixin):
    """Render source-specific classic cards with a generic Block Kit fallback."""

    def format(self, notification: Notification, *, include_metadata: bool = True) -> dict:
        """Render Slack Classic Cards using the Discord Classic v1 content contract."""

        source = str(notification.source or "").strip().casefold()
        if source == "xo":
            return self._format_xo_classic(notification)
        return self._format_discord_classic(notification)

    def _format_discord_classic(self, notification: Notification) -> dict:
        """Translate the shared Discord Classic embed into Slack attachments."""

        metadata = (
            notification.metadata
            if isinstance(notification.metadata, dict)
            else {}
        )
        source = str(notification.source or "").strip().casefold()
        icon_source = (
            source
            if source in self.PRODUCT_ICONS and source != "redfish"
            else "nowlert"
        )

        seed_embed = {}
        action = safe_action_url(metadata.get("action_link"))
        if action:
            seed_embed["url"] = action

        event_time = metadata.get("event_time") or notification.start_time
        if event_time:
            formatted_time = self._format_datetime(event_time)
            if formatted_time:
                seed_embed["fields"] = [
                    {
                        "name": "⏱️ Event time",
                        "value": formatted_time,
                    }
                ]

        classic = render_classic_embed_v1(
            notification,
            {"embeds": [seed_embed]},
        )
        embed = classic["embeds"][0]

        title = self._truncate(
            embed.get("title")
            or notification.title
            or notification.subject
            or "Notification",
            200,
        )
        description = self._slack_classic_mrkdwn(
            embed.get("description") or ""
        )
        fields = [
            self._slack_classic_field(field)
            for field in embed.get("fields", [])[:10]
            if isinstance(field, dict)
        ]
        footer = str(
            (embed.get("footer") or {}).get("text")
            or CLASSIC_FOOTER
        )[:300]
        title_link = safe_action_url(embed.get("url") or action)
        icon_url = self._slack_classic_icon_url(icon_source)

        attachment = {
            "fallback": title,
            "color": self._slack_classic_color(embed.get("color")),
            "blocks": self._slack_classic_blocks(
                title,
                description,
                fields,
                icon_url,
                title_link=title_link,
                footer=footer,
            ),
        }

        return self._sanitize_payload(
            {
                "attachments": [attachment],
            }
        )

    def _slack_classic_blocks(
        self,
        title,
        description,
        fields,
        icon_url,
        *,
        title_link="",
        footer=CLASSIC_FOOTER,
    ):
        """Render a compact Slack Classic card with visible product branding."""

        title_text = self._escape(title)
        if title_link:
            title_text = f"<{self._escape(title_link)}|{title_text}>"

        header_text = f"*{title_text}*"
        if description:
            header_text = f"{header_text}\n{description}"

        header = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": header_text[:3000],
            },
        }
        if icon_url:
            header["accessory"] = {
                "type": "image",
                "image_url": icon_url,
                "alt_text": "Nowlert integration",
            }

        blocks = [header]
        header_fields = []

        for field in fields:
            field_title = str(field.get("title") or "")
            field_value = str(field.get("value") or "").removesuffix("\n\u200b")
            if not field_title and not field_value:
                continue

            block_text = {
                "type": "mrkdwn",
                "text": (
                    f"*{self._escape(field_title)}*\n"
                    f"{field_value}"
                )[:2000],
            }
            if field.get("short"):
                header_fields.append(block_text)
                continue

            blocks.append(
                {
                    "type": "section",
                    "text": block_text,
                }
            )

        if header_fields:
            header["fields"] = header_fields[:10]

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": footer,
                    }
                ],
            }
        )
        return blocks

    def _slack_classic_icon_url(self, source):
        """Prefer padded artwork for Slack's fixed image-accessory slot."""

        normalized = str(source or "").strip().casefold()
        icon_url = self._product_icon_url(normalized)
        padded = self.DISCORD_PRODUCT_ICONS.get(normalized)
        if not icon_url or not padded:
            return icon_url
        return f"{icon_url.rsplit('/', 1)[0]}/{padded}"

    def _slack_classic_field(self, field):
        return {
            "title": self._truncate(field.get("name") or "", 200),
            "value": self._slack_classic_mrkdwn(
                field.get("value") or ""
            )[:1800],
            "short": bool(field.get("inline")),
        }

    def _slack_classic_mrkdwn(self, value):
        """Translate Discord Classic markdown into Slack mrkdwn safely."""

        text = str(value or "")
        parts = []
        cursor = 0

        for match in _MARKDOWN_LINK.finditer(text):
            parts.append(self._escape(text[cursor:match.start()]))

            label = match.group(1).strip()
            url = safe_action_url(match.group(2))
            if url:
                parts.append(
                    f"<{self._escape(url)}|{self._escape(label)}>"
                )
            else:
                parts.append(self._escape(match.group(0)))

            cursor = match.end()

        parts.append(self._escape(text[cursor:]))
        return "".join(parts).replace("**", "*")

    @staticmethod
    def _slack_classic_color(value):
        if isinstance(value, int):
            return f"#{value & 0xFFFFFF:06X}"
        rendered = str(value or "").strip()
        if not rendered:
            return "#3498DB"
        if rendered.startswith("#"):
            return rendered[:7]
        return f"#{rendered[:6]}"

    def _format_xo_classic(self, notification: Notification) -> dict:
        """Mirror the approved Discord Classic Xen Orchestra card in Slack."""

        status = str(notification.status or "").strip().casefold()
        failed = status in {"failure", "failed", "error", "critical"}
        skipped_count = int(getattr(notification, "vm_skipped", 0) or 0)
        skipped = status == "skipped" or (not failed and skipped_count > 0)

        if failed:
            color, icon, lifecycle = "#ED4245", "❌", "Backup Failed"
        elif skipped:
            color, icon, lifecycle = "#5865F2", "⏭️", "Backup Skipped"
        else:
            color, icon, lifecycle = "#57F287", "✅", "Backup Successful"

        job_name = str(
            getattr(notification, "job_name", "")
            or notification.title
            or notification.subject
            or "Xen Orchestra backup"
        ).strip()
        title = self._truncate(f"{icon} {lifecycle} — {job_name}", 200)

        vm_success = int(getattr(notification, "vm_success", 0) or 0)
        vm_failed = int(getattr(notification, "vm_failed", 0) or 0)
        vm_total = int(getattr(notification, "vm_total", 0) or 0)

        if failed:
            count = max(1, vm_failed)
            description = (
                f"Backup operation failed with {count} VM error."
                if count == 1
                else f"Backup operation failed with {count} VM errors."
            )
        elif skipped:
            protected = vm_success
            protected_label = "VM" if protected == 1 else "VMs"
            skipped_label = "VM was" if skipped_count == 1 else "VMs were"
            description = (
                f"{protected} {protected_label} protected successfully and "
                f"{skipped_count} {skipped_label} skipped by backup policy."
            )
        else:
            protected = vm_success or vm_total
            protected_label = "VM" if protected == 1 else "VMs"
            description = (
                f"{protected} {protected_label} protected successfully "
                "with no failures."
            )

        repository = str(getattr(notification, "repository", "") or "").strip()
        repository_parts = [
            part.strip()
            for part in repository.split("|")
            if part.strip()
        ]
        if len(repository_parts) >= 3:
            repository_parts = [repository_parts[-1], *repository_parts[:-1]]

        mode = str(getattr(notification, "mode", "") or "").strip()
        if mode:
            mode = mode[:1].upper() + mode[1:]
        storage_parts = list(repository_parts)
        if mode:
            storage_parts.append(mode)
        storage_value = " · ".join(storage_parts)

        fields = []
        for field in (
            self._classic_field(
                "⏱️ Duration",
                self._classic_code(getattr(notification, "duration", "")),
                short=True,
            ),
            self._classic_field(
                "📦 Transfer Size",
                self._classic_code(getattr(notification, "transfer_size", "")),
                short=True,
            ),
            self._classic_field(
                "🚀 Transfer Speed",
                self._classic_code(getattr(notification, "transfer_speed", "")),
                short=True,
            ),
            self._classic_field(
                "📁 Storage",
                self._classic_code(storage_value),
                short=True,
            ),
            self._classic_vm_field(
                "✅ Successful VMs",
                getattr(notification, "successful_vms", None),
                getattr(notification, "vm_details", None),
            ),
            self._classic_vm_field(
                "❌ Failed VMs",
                getattr(notification, "failed_vms", None),
                getattr(notification, "vm_details", None),
                include_error=True,
            ),
            self._classic_vm_field(
                "⏭️ Skipped VMs",
                getattr(notification, "skipped_vms", None),
                getattr(notification, "vm_details", None),
                include_error=True,
            ),
            self._classic_field(
                "🆔 Job ID",
                self._classic_code(getattr(notification, "job_id", "")),
            ),
        ):
            if field is not None:
                fields.append(field)

        icon_url = self._xo_slack_icon_url()
        attachment = {
            "fallback": title,
            "color": color,
            "blocks": self._xo_classic_blocks(
                title,
                description,
                fields[:10],
                icon_url,
            ),
        }

        return self._sanitize_payload(
            {
                "attachments": [attachment],
            }
        )

    def _xo_classic_blocks(self, title, description, fields, icon_url):
        """Render the XO Classic Card with a visible Block Kit icon."""

        header = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{self._escape(title)}*\n"
                    f"{self._escape(description)}"
                )[:3000],
            },
        }
        if icon_url:
            header["accessory"] = {
                "type": "image",
                "image_url": icon_url,
                "alt_text": "Xen Orchestra",
            }

        blocks = [header]
        header_fields = []
        job_id_value = ""

        for field in fields:
            title = str(field.get("title") or "")
            value = str(field.get("value") or "").removesuffix("\n\u200b")

            if title == "🆔 Job ID":
                job_id_value = value
                continue

            block_text = {
                "type": "mrkdwn",
                "text": (
                    f"*{self._escape(title)}*\n"
                    f"{value}"
                )[:2000],
            }
            if field.get("short"):
                header_fields.append(block_text)
                continue

            blocks.append(
                {
                    "type": "section",
                    "text": block_text,
                }
            )

        if header_fields:
            header["fields"] = header_fields[:10]

        if job_id_value:
            job_line = f"*🆔 Job ID* {job_id_value}"
            if (
                len(blocks) > 1
                and blocks[-1].get("type") == "section"
                and isinstance(blocks[-1].get("text"), dict)
            ):
                current = str(blocks[-1]["text"].get("text") or "")
                blocks[-1]["text"]["text"] = (
                    f"{current}\n{job_line}"
                )[:3000]
            else:
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": job_line,
                        },
                    }
                )

        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": CLASSIC_FOOTER,
                    }
                ],
            }
        )
        return blocks

    def _xo_slack_icon_url(self):
        """Use the padded XO artwork so Slack renders a smaller visible mark."""

        icon_url = self._product_icon_url("xo")
        suffix = "/xen-orchestra.png"
        if not icon_url or not icon_url.endswith(suffix):
            return icon_url
        return f"{icon_url[:-len(suffix)]}/discord/xen-orchestra.png"

    def _classic_vm_field(
        self,
        name,
        values,
        details,
        *,
        include_error: bool = False,
        space_after: bool = False,
    ):
        if not isinstance(values, list) or not values:
            return None
        if not isinstance(details, dict):
            details = {}

        vm_names = [
            str(value or "").strip()
            for value in values
            if str(value or "").strip()
        ]
        if not vm_names:
            return None

        lines = []
        shown = vm_names[:10]
        for vm_name in shown:
            item = details.get(vm_name)
            if not isinstance(item, dict):
                item = {}
            size = str(item.get("size") or "").strip()
            line = f"*{self._escape(vm_name)}*"
            if size:
                line += f" · {self._classic_code(size)}"
            lines.append(line)

            if include_error and str(item.get("error") or "").strip():
                lines.append(
                    f"*Error:* {self._classic_code(item.get('error'))}"
                )

        remaining = len(vm_names) - len(shown)
        if remaining > 0:
            lines.append(f"… and {remaining} more")

        return self._classic_field(
            f"{name} · {len(vm_names)}",
            "\n".join(lines),
            space_after=space_after,
        )

    def _classic_field(
        self,
        title,
        value,
        *,
        short: bool = False,
        space_after: bool = False,
    ):
        rendered = str(value or "").strip()
        if not rendered:
            return None
        if space_after:
            rendered = f"{rendered}\n\u200b"
        return {
            "title": self._truncate(title, 200),
            "value": rendered[:1800],
            "short": bool(short),
        }

    def _classic_code(self, value):
        rendered = " ".join(
            str(value or "").replace(chr(96), "'").splitlines()
        ).strip()
        if not rendered:
            return ""
        if len(rendered) > 900:
            rendered = rendered[:899].rstrip() + "…"
        return f"`{self._escape(rendered)}`"

    def _field(self, label, value):
        return {
            "type": "mrkdwn",
            "text": f"*{self._escape(label)}*\n{self._escape(value)[:1800]}",
        }

    @staticmethod
    def _escape(value) -> str:
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )