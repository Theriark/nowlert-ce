"""Schema-12 routing/filter fallback adapters.

Destination filters must be evaluated before the existing dedicated-vs-wildcard
fallback decision. With reusable Routes this means expanding each Route to its
Destinations first, applying Destination Filters, then choosing dedicated
candidates globally (or wildcard candidates when no dedicated candidate remains)
and finally de-duplicating by Destination.
"""

from __future__ import annotations

from dataclasses import replace

from integrations.catalog import canonical_source
from storage.delivery import DeliverySummary
from storage.ownership import Actor, OwnershipPolicy


def _normalized(value) -> str:
    return str(value or "").strip().casefold()


def routing_only_matching(self, actor, owner_user_id, notification):
    OwnershipPolicy.require_read(actor, str(owner_user_id))
    source = canonical_source(notification.source)
    observed_input = _normalized((notification.metadata or {}).get("_input_type"))
    with self.database.connect() as connection:
        rows = connection.execute(
            """
            SELECT routes.*
            FROM routes
            JOIN users ON users.id = routes.owner_user_id
            WHERE routes.owner_user_id = ?
              AND routes.enabled = 1
              AND users.enabled = 1
              AND (routes.source = ? OR routes.source = '*')
            ORDER BY routes.priority, routes.name_normalized
            """,
            (str(owner_user_id), source),
        ).fetchall()
    candidates = []
    for row in rows:
        route = self._route(row)
        if route.input_type and _normalized(route.input_type) != observed_input:
            continue
        candidates.append(replace(route, filters={}))
    return candidates


def filtered_deliver(self, actor: Actor, notification) -> DeliverySummary:
    self.filters.migrate_legacy_route_filters()
    routes = self.routes.matching(actor, actor.user_id, notification)

    # Expand one Route at a time so a Destination reached by both a dedicated
    # and wildcard Route remains available to the fallback decision.
    candidates = []
    for route in routes:
        candidates.extend(self.relationships.expand(actor, [route]))

    allowed = [
        candidate
        for candidate in candidates
        if self.filters.matches(actor, candidate.destination_id, notification)
    ]
    specific = [candidate for candidate in allowed if candidate.route.source != "*"]
    selected = specific if specific else [
        candidate for candidate in allowed if candidate.route.source == "*"
    ]

    matching = []
    seen_destinations = set()
    for candidate in selected:
        if candidate.destination_id in seen_destinations:
            continue
        seen_destinations.add(candidate.destination_id)
        matching.append(candidate)
    return self._deliver_candidates(actor, notification, matching)


def apply_filtering_v12(routing_only_class, filtered_delivery_class):
    routing_only_class.matching = routing_only_matching
    filtered_delivery_class.deliver = filtered_deliver
