"""Filtering view over system Route definitions that are always available."""

from __future__ import annotations

from integrations.catalog import canonical_source
from integrations.filtering import filter_schemas, sources_for_input
from storage.destination_access import AccessControlledDestinationFilterStore


class SystemDestinationFilterStore(AccessControlledDestinationFilterStore):
    """Treat every bound system Route as available regardless of legacy enable state."""

    def available_sources(self, actor, destination_id):
        self._destination(actor, destination_id)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT routes.source, routes.input_type
                FROM route_destinations
                JOIN routes ON routes.id = route_destinations.route_id
                WHERE route_destinations.destination_id = ?
                ORDER BY routes.priority, routes.name_normalized
                """,
                (str(destination_id),),
            ).fetchall()
        catalogue_sources = [item["source"] for item in filter_schemas()]
        found = set()
        for row in rows:
            source = canonical_source(str(row["source"]))
            if source == "*":
                found.update(sources_for_input(str(row["input_type"] or "")))
            elif source in catalogue_sources:
                found.add(source)
        return tuple(source for source in catalogue_sources if source in found)
