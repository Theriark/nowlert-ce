"""Every shipped integration must honor destination route selection."""

import pytest

from integrations.catalog import route_options
from models import Notification
from storage.delivery import DeliveryResult, DeliveryHistoryStore, PlatformDeliveryService
from storage.destination_access import AccessControlledRouteDestinationStore
from storage.destinations import DestinationStore
from storage.routing_bridge import PlatformRoutingBridge
from storage.routes import RouteStore
from storage.filtering import DestinationFilterStore, FilteredPlatformDeliveryService, RoutingOnlyRouteStore
from storage.secrets import SecretStore
from types import SimpleNamespace
from test_system_routing_fallback import database_with_admin


OPTIONS = [option for option in route_options() if option["source"] != "*"]


@pytest.mark.parametrize("option", OPTIONS, ids=lambda item: f"{item['source']}-{item['input_type']}")
@pytest.mark.parametrize("engine", ["system", "filtered", "one-pass"])
def test_delivery_requires_explicit_assignment_even_with_fallback(tmp_path, option, engine):
    database, actor = database_with_admin(tmp_path)
    destinations = DestinationStore(database)
    selected = destinations.create(actor, actor.user_id, "Selected", "webhook", settings={})
    unselected = destinations.create(actor, actor.user_id, "Unselected", "webhook", settings={})
    routes = RouteStore(database)
    fallback = routes.create(actor, actor.user_id, "Fallback", "*", input_type=option["input_type"])
    dedicated = routes.create(actor, actor.user_id, "Dedicated", option["source"], input_type=option["input_type"])
    relationships = AccessControlledRouteDestinationStore(database)
    relationships.replace_for_destination(actor, selected.id, [fallback.id])
    relationships.replace_for_destination(actor, unselected.id, [fallback.id])
    sent = []

    class Registry:
        def delivery_adapters(self):
            return {"webhook": lambda target, secret, event: (
                sent.append(target.id) or DeliveryResult(True, response_status=204))}

    bridge = PlatformRoutingBridge(database, registry=Registry())
    if engine != "system":
        service_class = FilteredPlatformDeliveryService if engine == "filtered" else PlatformDeliveryService
        kwargs = {"filters": DestinationFilterStore(database)} if engine == "filtered" else {}
        route_store = RoutingOnlyRouteStore(database) if engine == "filtered" else routes
        service = service_class(route_store, destinations, SecretStore(database),
                                DeliveryHistoryStore(database), Registry().delivery_adapters(), **kwargs)
        bridge = SimpleNamespace(route=lambda event: service.deliver(actor, event))
    event = Notification(source=option["source"], title="Route selection probe",
                         metadata={"_input_type": option["input_type"]})
    assert bridge.route(event).delivered == 0
    assert sent == []
    relationships.replace_for_destination(actor, selected.id, [fallback.id, dedicated.id])
    assert bridge.route(event).delivered == 1
    assert sent == [selected.id]
    relationships.replace_for_destination(actor, selected.id, [fallback.id])
    assert bridge.route(event).delivered == 0
    assert sent == [selected.id]


@pytest.mark.parametrize("source,input_type", [("generic", "smtp"), ("generic_http", "http"), ("redfish", "redfish")])
def test_generic_events_still_use_selected_fallback(tmp_path, source, input_type):
    database, actor = database_with_admin(tmp_path)
    destination = DestinationStore(database).create(actor, actor.user_id, "Generic", "webhook", settings={})
    routes = RouteStore(database)
    fallback = routes.create(actor, actor.user_id, "Generic fallback", "*", destination.id, input_type=input_type)
    event = Notification(source=source, metadata={"_input_type": input_type})
    assert RouteStore.matches(fallback, event)
