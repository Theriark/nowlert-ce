"""Persistent state and security services for the Nowlert v2 platform."""

from storage.database import Database
from storage.api_tokens import (
    APIToken,
    APITokenStore,
    TokenCredentials,
    TokenPrincipal,
)
from storage.audit_events import AuditEvent, AuditEventStore
from storage.backups import StateBackup, StateBackupStore
from storage.bootstrap import BootstrapCredential, BootstrapStatus, BootstrapStore
from storage.delivery import (
    DeliveryAttempt,
    DeliveryHistoryStore,
    DeliveryResult,
    DeliverySummary,
    PlatformDeliveryService,
)
from storage.destinations import Destination, DestinationStore
from storage.ownership import Actor, OwnershipPolicy
from storage.portability import ImportPlan, PlatformPortabilityService
from storage.route_destinations import RouteDestinationCandidate, RouteDestinationStore
from storage.routes import Route, RouteStore
from storage.secrets import SecretMetadata, SecretStore
from storage.sessions import SessionCredentials, SessionPrincipal, SessionStore
from storage.users import User, UserStore

# Compatibility adapters keep the legacy configuration bridge and the existing
# destination-filter fallback semantics while Routes move to schema 12.
from storage.configuration_sync import UnifiedConfigurationService
from storage.configuration_sync_v12 import apply_configuration_sync_v12
from storage.filtering import FilteredPlatformDeliveryService, RoutingOnlyRouteStore
from storage.filtering_v12 import apply_filtering_v12

apply_configuration_sync_v12(UnifiedConfigurationService)
apply_filtering_v12(RoutingOnlyRouteStore, FilteredPlatformDeliveryService)

__all__ = [
    "Actor",
    "APIToken",
    "APITokenStore",
    "AuditEvent",
    "AuditEventStore",
    "BootstrapCredential",
    "BootstrapStatus",
    "BootstrapStore",
    "StateBackup",
    "StateBackupStore",
    "Database",
    "DeliveryAttempt",
    "DeliveryHistoryStore",
    "DeliveryResult",
    "DeliverySummary",
    "Destination",
    "DestinationStore",
    "OwnershipPolicy",
    "ImportPlan",
    "PlatformPortabilityService",
    "PlatformDeliveryService",
    "Route",
    "RouteDestinationCandidate",
    "RouteDestinationStore",
    "RouteStore",
    "SecretMetadata",
    "SecretStore",
    "SessionCredentials",
    "SessionPrincipal",
    "SessionStore",
    "TokenCredentials",
    "TokenPrincipal",
    "User",
    "UserStore",
]
