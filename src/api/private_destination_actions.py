"""Bounded administrator preview/test operations for private Destinations.

The acceptance access model intentionally keeps another user's private
Destination configuration hidden from administrators.  This module adds only
the two operational actions explicitly surfaced by the Destinations overview:
preview and one-shot test delivery.  Read, edit, delete, sharing, filtering,
settings, and credentials continue through the existing privacy boundary.
"""

from __future__ import annotations

from api.access_acceptance import PlatformAPI as AcceptancePlatformAPI
from api.response import APIResponse


class PlatformAPI(AcceptancePlatformAPI):
    """Permit bounded admin operations without exposing private configuration."""

    def _is_private_admin_operation(self, actor, destination_id: str) -> bool:
        if self.yaml_resource_authority or not actor.is_admin:
            return False
        row = self.destination_access.destination_row(destination_id)
        return (
            str(row["owner_user_id"]) != actor.user_id
            and not bool(row["shared"])
        )

    def _destination_resource(self, method, payload, actor, destination_id, action):
        if (
            action not in {"preview", "test"}
            or not self._is_private_admin_operation(actor, destination_id)
        ):
            return super()._destination_resource(
                method,
                payload,
                actor,
                destination_id,
                action,
            )

        if method != "POST":
            return self._method_not_allowed("POST")

        data = self._object(payload, {"event"})
        notification = self._notification(data.get("event"))
        row = self.destination_access.destination_row(destination_id)
        destination = self.destinations._destination(row)

        if action == "preview":
            try:
                adapter = self.registry.get(destination.output_type)
                preview = adapter.preview(destination, notification)
            except (KeyError, TypeError, ValueError):
                self.audit.write(
                    actor,
                    "destination.preview",
                    "destination",
                    destination_id,
                    "invalid",
                )
                raise ValueError(
                    "destination cannot preview this notification"
                ) from None
            self.audit.write(
                actor,
                "destination.preview",
                "destination",
                destination_id,
                "success",
                {"output_type": destination.output_type, "private_operation": True},
            )
            return APIResponse(
                200,
                {
                    "preview": {
                        "output_type": preview.output_type,
                        "content_type": preview.content_type,
                        "payload": preview.payload,
                        "metadata": preview.metadata,
                    }
                },
            )

        result = self.outputs.test_delivery(
            actor,
            destination_id,
            notification,
        )
        return APIResponse(
            200,
            {"result": self._delivery_result(result)},
        )
