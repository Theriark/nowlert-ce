"""Bounded administrator preview/test operations for private Destinations.

The acceptance access model intentionally keeps another user's private
Destination configuration hidden from administrators.  This module adds only
the two operational actions explicitly surfaced by the Destinations overview:
preview and one-shot test delivery.  Read, edit, delete, sharing, filtering,
settings, and credentials continue through the existing privacy boundary.

It is also the outermost API layer, so it releases a destination's credential
record after a delete and clears credential records left behind by earlier
deletes when an administrator removes their owner.
"""

from __future__ import annotations

from api.access_acceptance import PlatformAPI as AcceptancePlatformAPI
from api.response import APIResponse
from logger import log


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

    def _destination_secret_id(self, destination_id: str) -> str | None:
        try:
            row = self.destinations._record(destination_id)
        except KeyError:
            return None
        return str(row["secret_id"]) if row["secret_id"] else None

    def _release_secret(self, actor, secret_id: str) -> None:
        """Delete a credential record nothing references any more."""

        try:
            self.secrets.delete_if_unreferenced(actor, secret_id)
        except (KeyError, PermissionError, ValueError, OSError):
            log.warning("Credential cleanup failed for a deleted destination")

    def _purge_unreferenced_secrets(self, actor, owner_user_id: str) -> None:
        """Remove credential records left behind by earlier destination deletes."""

        for secret_id in self.secrets.unreferenced_ids(owner_user_id):
            self._release_secret(actor, secret_id)

    def _user_resource(self, method, payload, actor, user_id, action):
        if (
            method == "DELETE"
            and action is None
            and actor.is_admin
            and user_id != actor.user_id
        ):
            self._purge_unreferenced_secrets(actor, user_id)
        return super()._user_resource(method, payload, actor, user_id, action)

    def _destination_resource(self, method, payload, actor, destination_id, action):
        if (
            method == "DELETE"
            and action is None
            and not self.yaml_resource_authority
        ):
            secret_id = self._destination_secret_id(destination_id)
            response = super()._destination_resource(
                method,
                payload,
                actor,
                destination_id,
                action,
            )
            if response.status < 300 and secret_id:
                self._release_secret(actor, secret_id)
            return response

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
