"""Authenticated, owner-scoped HTTP contract for the Nowlert v2 platform."""

from __future__ import annotations

import json
import os
import re
import signal
import threading
import uuid
import time

from http.cookies import SimpleCookie
from urllib.parse import unquote

from api.response import APIResponse
from environment import compatible_environment
from integrations.catalog import integrations, route_options
from logger import log
from api.security import Principal, RateLimiter
from outputs.platform import PlatformOutputRegistry
from outputs.service import PlatformOutputService
from outputs.settings import normalize_output_settings
from storage.api_tokens import APITokenStore
from storage.audit_events import AuditEventStore
from storage.backups import StateBackupStore
from storage.bootstrap import BootstrapStore
from storage.configuration_bridge import ConfigurationBridgeService
from storage.configuration_sync import UnifiedConfigurationService
from storage.delivery import DeliveryHistoryStore, PlatformDeliveryService
from storage.destinations import DestinationStore
from inputs.email_mailboxes import MailboxConnectionService
from storage.ownership import Actor
from storage.portability import PlatformPortabilityService
from storage.routes import RouteStore
from storage.routes import route_priority_name
from storage.sanitize import sanitize_text
from storage.validation import ConflictError
from storage.secrets import SecretStore
from storage.sessions import SessionStore
from storage.users import UserStore
from storage.health import HealthCheckService
from storage.housekeeping import HousekeepingService
from storage.integrations import IntegrationCategoryStore
from storage.mfa import (
    generate_totp_secret,
    provisioning_qr_data_uri,
    provisioning_uri,
    verify_totp,
)
from storage.backup_scheduler import BackupScheduler
from storage.backup_targets import BackupTargetStore
from version import VERSION


_RESOURCE_ID = re.compile(r"^[0-9a-f]{32}$")
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class PlatformAPI:
    """Expose platform state without mixing session and application authority."""

    def __init__(
        self,
        database,
        dispatcher,
        configuration,
        *,
        registry=None,
        config_service=None,
        reboot_callback=None,
    ):
        self.database = database
        self.dispatcher = dispatcher
        self.configuration = configuration
        self.audit = AuditEventStore(database)
        self.users = UserStore(database)
        self.bootstrap = BootstrapStore(database, users=self.users)
        self.sessions = SessionStore(database)
        self.tokens = APITokenStore(database, audit=self.audit)
        self.secrets = SecretStore(database)
        self.email_connections = MailboxConnectionService(
            database,
            secrets=self.secrets,
            audit=self.audit,
        )
        self.email_pipeline = self.email_connections.processor
        self.email_rules = self.email_pipeline.rules
        self.portability = PlatformPortabilityService(
            database,
            secrets=self.secrets,
            audit=self.audit,
        )
        backup_config_path = (
            getattr(config_service, "path", None)
            if config_service is not None
            and getattr(config_service, "reloadable", False)
            else None
        )
        self.backups = StateBackupStore(
            database,
            config_path=backup_config_path,
            audit=self.audit,
            retention=configuration.get(
                "platform",
                "backup_retention",
                default=20,
            ),
        )
        self.destinations = DestinationStore(database, audit=self.audit)
        self.routes = RouteStore(database, audit=self.audit)
        self.history = DeliveryHistoryStore(database)
        self.integration_categories = IntegrationCategoryStore(database)
        self.registry = registry or PlatformOutputRegistry()
        self.outputs = PlatformOutputService(
            self.destinations,
            self.secrets,
            self.registry,
            audit=self.audit,
        )
        self.delivery = PlatformDeliveryService(
            self.routes,
            self.destinations,
            self.secrets,
            self.history,
            self.registry.delivery_adapters(),
        )
        self.configuration_bridge = (
            ConfigurationBridgeService(
                config_service,
                self.portability,
                self.backups,
                audit=self.audit,
            )
            if config_service is not None
            else None
        )
        self.configuration_sync = (
            UnifiedConfigurationService(
                config_service,
                database,
                audit=self.audit,
            )
            if config_service is not None
            and getattr(config_service, "reloadable", True)
            else None
        )
        if self.configuration_sync is not None:
            status = self.configuration_sync.synchronize(force=True)
            if status.errors:
                log.error(
                    "Configuration migration/settings load failed: %s",
                    "; ".join(status.errors),
                )
        self.health = HealthCheckService(database, self.configuration_sync)
        self.housekeeping = HousekeepingService(database, audit=self.audit)
        self.backup_scheduler = BackupScheduler(
            database,
            configuration,
            config_path=backup_config_path,
        )
        self.backup_targets = BackupTargetStore(
            database,
            configuration,
            secrets=self.secrets,
        )
        self.reboot_callback = reboot_callback or self._terminate_process
        self.token_limiter = RateLimiter()
        self.login_limiter = RateLimiter()
        self.bootstrap_limiter = RateLimiter()
        self.session_limiter = RateLimiter()

    @property
    def secure_cookies(self) -> bool:
        return self.configuration.get(
            "platform",
            "secure_cookies",
            default=False,
        ) is True

    @property
    def yaml_resource_authority(self) -> bool:
        return (
            self.configuration_sync is not None
            and not self.configuration_sync.database_authoritative
        )

    def handle(self, method, path, payload, headers, client) -> APIResponse:
        method = str(method or "").upper()
        try:
            if path == "/api/v2/bootstrap":
                return self._bootstrap(method, payload, client)
            if path == "/api/v2/session" and method == "POST":
                return self._login(payload, client)
            if path == "/api/v2/events" and method == "POST":
                return self._submit_event(payload, headers, client)
            principal = self._session(
                headers,
                require_csrf=method not in _SAFE_METHODS,
                touch=(path == "/api/v2/session" or method not in _SAFE_METHODS),
            )
        except Exception as error:
            return self._unexpected(path, error)
        if principal is None:
            return APIResponse(401, {"error": "authentication required"})
        # A valid session refresh is the browser's authentication liveness
        # check. Do not consume the workspace request budget for it, otherwise
        # a burst of safe GETs can make a valid session look signed out.
        if path == "/api/v2/session" and method == "GET":
            return self._session_endpoint(method, principal)
        session_rate = Principal(
            name=f"platform-session:{principal.session_id}",
            role=principal.role,
            sources=frozenset(),
            rate_limit_per_minute=240,
        )
        if not self.session_limiter.allow(session_rate, str(client)):
            return APIResponse(429, {"error": "rate limit exceeded"})
        actor = principal.actor

        try:
            if path == "/api/v2/session":
                return self._session_endpoint(method, principal)
            if path == "/api/v2/users":
                return self._users_endpoint(method, payload, actor)
            if path == "/api/v2/account/password":
                return self._own_password(method, payload, principal)
            if path == "/api/v2/account/avatar":
                return self._own_avatar(method, payload, principal)
            if path == "/api/v2/account/mfa/setup":
                return self._own_mfa_setup(method, principal)
            if path == "/api/v2/account/mfa":
                return self._own_mfa(method, payload, principal)
            if path == "/api/v2/integrations":
                return self._integrations_endpoint(method, payload, actor)
            if path == "/api/v2/integration-settings":
                return self._integration_settings_endpoint(method, payload, actor)
            if path.startswith("/api/v2/integration-settings/"):
                source = unquote(path[len("/api/v2/integration-settings/"):])
                return self._integration_settings_resource(
                    method, payload, actor, source
                )
            if path == "/api/v2/preferences":
                return self._preferences_endpoint(method, payload, actor)
            if path == "/api/v2/source-categories":
                return self._source_categories_endpoint(method, payload, actor)
            if path.startswith("/api/v2/source-categories/") and method == "DELETE":
                source = unquote(path[len("/api/v2/source-categories/"):])
                return self._source_categories_endpoint(
                    method, {"source": source}, actor
                )
            if path == "/api/v2/version":
                return self._version_endpoint(method)
            if path == "/api/v2/tokens":
                return self._tokens_endpoint(method, payload, actor)
            if path == "/api/v2/email-overview":
                return self._email_overview_endpoint(method, actor)
            if path == "/api/v2/email-activity":
                return self._email_activity_endpoint(method, actor)
            if path == "/api/v2/email-groups":
                return self._email_groups_endpoint(method, payload, actor)
            email_group_match = re.fullmatch(
                r"/api/v2/email-groups/([0-9a-f]{32})",
                path,
            )
            if email_group_match:
                return self._email_group_resource(
                    method,
                    payload,
                    actor,
                    email_group_match.group(1),
                )
            if path == "/api/v2/email-rules":
                return self._email_rules_endpoint(method, payload, actor)
            if path == "/api/v2/email-rules/evaluate":
                return self._email_rule_evaluate(method, payload, actor)
            email_rule_match = re.fullmatch(
                r"/api/v2/email-rules/([0-9a-f]{32})",
                path,
            )
            if email_rule_match:
                return self._email_rule_resource(
                    method,
                    payload,
                    actor,
                    email_rule_match.group(1),
                )
            email_message_action = re.fullmatch(
                r"/api/v2/email-messages/([0-9a-f]{32})/"
                r"(reprocess|preview|mute-similar|ignore-sender|change-severity)",
                path,
            )
            if email_message_action:
                return self._email_message_action(
                    method,
                    payload,
                    actor,
                    email_message_action.group(1),
                    email_message_action.group(2),
                )
            if path == "/api/v2/email-mailboxes":
                return self._email_mailboxes_endpoint(method, payload, actor)
            if path == "/api/v2/email-mailboxes/oauth-complete":
                return self._email_oauth_complete(method, payload, actor)
            email_mailbox_match = re.fullmatch(
                r"/api/v2/email-mailboxes/([0-9a-f]{32})(?:/(oauth-start|oauth-complete|sync))?",
                path,
            )
            if email_mailbox_match:
                return self._email_mailbox_resource(
                    method,
                    payload,
                    actor,
                    email_mailbox_match.group(1),
                    email_mailbox_match.group(2),
                )
            if path == "/api/v2/destinations":
                return self._destinations_endpoint(method, payload, actor)
            if path == "/api/v2/routes":
                return self._routes_endpoint(method, payload, actor)
            if path == "/api/v2/deliveries":
                return self._deliveries_endpoint(method, actor)
            delivery_page_size = re.fullmatch(
                r"/api/v2/deliveries/page/(\d+)/size/(\d+)", path
            )
            if delivery_page_size:
                return self._deliveries_page_endpoint(
                    method,
                    actor,
                    int(delivery_page_size.group(1)),
                    int(delivery_page_size.group(2)),
                )
            delivery_page = re.fullmatch(r"/api/v2/deliveries/page/(\d+)", path)
            if delivery_page:
                return self._deliveries_page_endpoint(method, actor, int(delivery_page.group(1)))
            if path == "/api/v2/audit-events":
                return self._audit_endpoint(method, actor)
            audit_page_size = re.fullmatch(
                r"/api/v2/audit-events/page/(\d+)/size/(\d+)", path
            )
            if audit_page_size:
                return self._audit_page_endpoint(
                    method,
                    actor,
                    int(audit_page_size.group(1)),
                    int(audit_page_size.group(2)),
                )
            audit_page = re.fullmatch(r"/api/v2/audit-events/page/(\d+)", path)
            if audit_page:
                return self._audit_page_endpoint(method, actor, int(audit_page.group(1)))
            if path == "/api/v2/health-checks":
                return self._health_endpoint(method, actor)
            if path == "/api/v2/housekeeping":
                return self._housekeeping_endpoint(method, payload, actor)
            if path == "/api/v2/backup-settings":
                return self._backup_settings_endpoint(method, payload, actor)
            if path == "/api/v2/backup-targets":
                return self._backup_targets_endpoint(method, payload, actor)
            if path == "/api/v2/backups/run":
                return self._backup_run_endpoint(method, payload, actor)
            if path == "/api/v2/reboot":
                return self._reboot_endpoint(method, payload, actor)
            if path == "/api/v2/portability/export":
                return self._portability_export(method, actor)
            if path == "/api/v2/portability/preview":
                return self._portability_preview(method, payload, actor)
            if path == "/api/v2/portability/import":
                return self._portability_import(method, payload, actor)
            if path == "/api/v2/migrations/v1/preview":
                return self._v1_migration_preview(method, payload, actor)
            if path == "/api/v2/migrations/v1/import":
                return self._v1_migration_import(method, payload, actor)
            if path == "/api/v2/configuration/inventory":
                return self._configuration_inventory(method, actor)
            if path == "/api/v2/configuration/migration/preview":
                return self._configuration_migration_preview(method, actor)
            if path == "/api/v2/configuration/migration/apply":
                return self._configuration_migration_apply(method, payload, actor)
            if path == "/api/v2/configuration/routing-authority":
                return self._configuration_authority(method, payload, actor)
            if path == "/api/v2/backups":
                return self._backups_endpoint(method, actor)
            response = self._resource_endpoint(method, path, payload, actor)
            if response is not None:
                return response
            return APIResponse(404, {"error": "resource not found"})
        except ConflictError as error:
            return APIResponse(
                409,
                {
                    "error": sanitize_text(error),
                    "code": "resource_conflict",
                    "path": path,
                },
            )
        except KeyError as error:
            return APIResponse(
                404,
                {
                    "error": sanitize_text(error) or "resource not found",
                    "code": "resource_not_found",
                    "path": path,
                },
            )
        except PermissionError as error:
            return APIResponse(
                403,
                {
                    "error": sanitize_text(error) or "operation is not permitted",
                    "code": "operation_not_permitted",
                    "path": path,
                },
            )
        except (TypeError, ValueError) as error:
            return APIResponse(
                400,
                {
                    "error": sanitize_text(error) or "request is invalid",
                    "code": "validation_error",
                    "path": path,
                },
            )
        except Exception as error:
            return self._unexpected(path, error)

    def _login(self, payload, client) -> APIResponse:
        limiter_principal = Principal(
            name="platform-login",
            role="application",
            sources=frozenset(),
            rate_limit_per_minute=10,
        )
        if not self.login_limiter.allow(limiter_principal, str(client)):
            return APIResponse(429, {"error": "rate limit exceeded"})
        if not isinstance(payload, dict) or set(payload) - {"username", "password", "otp"}:
            return APIResponse(400, {"error": "request is invalid"})
        user = self.users.authenticate(
            str(payload.get("username") or ""),
            str(payload.get("password") or ""),
        )
        if user is None:
            self.audit.write(None, "session.login", "session", None, "denied")
            return APIResponse(401, {"error": "invalid credentials"})
        if user.mfa_enabled:
            otp = str(payload.get("otp") or "").strip()
            if not otp:
                self.audit.write(
                    user.actor,
                    "session.mfa",
                    "session",
                    None,
                    "required",
                )
                return APIResponse(
                    401,
                    {
                        "error": "multi-factor authentication required",
                        "code": "mfa_required",
                    },
                )
            secret = self._mfa_secret(user)
            if secret is None or not verify_totp(secret, otp):
                self.audit.write(
                    user.actor,
                    "session.mfa",
                    "session",
                    None,
                    "denied",
                )
                return APIResponse(
                    401,
                    {
                        "error": "authenticator code is invalid",
                        "code": "mfa_invalid",
                    },
                )
        credentials = self.sessions.create(user.id)
        self.audit.write(
            user.actor,
            "session.login",
            "session",
            credentials.session_id,
            "success",
        )
        return self._session_response(user, credentials)

    def _bootstrap(self, method, payload, client) -> APIResponse:
        status = self.bootstrap.status()
        if method == "GET":
            return APIResponse(
                200,
                {
                    "required": status.required,
                    "expires_at": status.expires_at,
                },
                (("Cache-Control", "no-store"),),
            )
        if method != "POST":
            return self._method_not_allowed("GET, POST")
        if not status.required:
            return APIResponse(409, {"error": "platform setup is already complete"})
        limiter_principal = Principal(
            name="platform-bootstrap",
            role="application",
            sources=frozenset(),
            rate_limit_per_minute=5,
        )
        if not self.bootstrap_limiter.allow(limiter_principal, str(client)):
            return APIResponse(429, {"error": "rate limit exceeded"})
        if not isinstance(payload, dict) or set(payload) != {
            "token",
            "username",
            "password",
        }:
            return APIResponse(400, {"error": "request is invalid"})
        try:
            user = self.bootstrap.consume(
                str(payload.get("token") or ""),
                str(payload.get("username") or ""),
                str(payload.get("password") or ""),
            )
        except PermissionError:
            self.audit.write(None, "platform.bootstrap", "user", None, "denied")
            return APIResponse(401, {"error": "setup token is invalid or expired"})
        except ValueError:
            return APIResponse(400, {"error": "setup account details are invalid"})
        self.audit.write(
            user.actor,
            "platform.bootstrap",
            "user",
            user.id,
            "success",
        )
        return self._session_response(user)

    def _session_response(self, user, credentials=None) -> APIResponse:
        credentials = credentials or self.sessions.create(user.id)
        headers = (
            # Accepted CWE-614 exception: platform.secure_cookies: false is an
            # explicit opt-in compatibility mode for trusted-LAN HTTP.
            # HTTPS mode uses __Host-nowlert_session with Secure, HttpOnly,
            # SameSite=Strict, Path=/, and no Domain; regression tests enforce both modes.
            # no-dd-sa:datadog/python-insecurecookie
            ("Set-Cookie", credentials.cookie(secure=self.secure_cookies)),
            ("Cache-Control", "no-store"),
        )
        return APIResponse(
            200,
            {
                "user": self._user(user),
                "csrf_token": credentials.csrf_token,
                "expires_at": credentials.expires_at,
                "idle_expires_at": credentials.idle_expires_at,
                "cookie_mode": "secure" if self.secure_cookies else "standard",
            },
            headers,
        )

    def _session_endpoint(self, method, principal) -> APIResponse:
        if method == "GET":
            return APIResponse(
                200,
                {
                    "user": self._user(self.users.get(principal.user_id)),
                    "csrf_token": principal.csrf_token,
                    "expires_at": principal.expires_at,
                    "idle_expires_at": principal.idle_expires_at,
                    "csrf_required": True,
                    "cookie_mode": "secure" if self.secure_cookies else "standard",
                },
                (("Cache-Control", "no-store"),),
            )
        if method == "DELETE":
            self.sessions.revoke(principal.session_id)
            self.audit.write(
                principal.actor,
                "session.logout",
                "session",
                principal.session_id,
                "success",
            )
            return APIResponse(204, None, self._clear_cookies())
        return self._method_not_allowed("GET, DELETE")

    def _users_endpoint(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if method == "GET":
            return APIResponse(200, {"users": [self._user(item) for item in self.users.list()]})
        if method == "POST":
            data = self._object(payload, {"username", "password", "role"})
            user = self.users.create(
                data.get("username"),
                data.get("password"),
                data.get("role", "user"),
            )
            self.audit.write(actor, "user.create", "user", user.id, "success")
            return APIResponse(201, {"user": self._user(user)})
        return self._method_not_allowed("GET, POST")

    def _own_password(self, method, payload, principal) -> APIResponse:
        if method != "PUT":
            return self._method_not_allowed("PUT")
        data = self._object(payload, {"current_password", "new_password"})
        user = self.users.authenticate(
            principal.username,
            str(data.get("current_password") or ""),
        )
        if user is None:
            return APIResponse(403, {"error": "operation is not permitted"})
        self.users.reset_password(user.id, data.get("new_password"))
        self.audit.write(user.actor, "user.password", "user", user.id, "success")
        return APIResponse(204, None, self._clear_cookies())

    def _own_avatar(self, method, payload, principal) -> APIResponse:
        if method == "PUT":
            data = self._object(payload, {"image_data"})
            if "image_data" not in data:
                raise ValueError("profile picture is required")
            user = self.users.set_avatar(principal.user_id, data.get("image_data"))
            self.audit.write(user.actor, "user.avatar", "user", user.id, "success")
            return APIResponse(200, {"user": self._user(user)})
        if method == "DELETE":
            user = self.users.set_avatar(principal.user_id, None)
            self.audit.write(user.actor, "user.avatar", "user", user.id, "success")
            return APIResponse(200, {"user": self._user(user)})
        return self._method_not_allowed("PUT, DELETE")

    def _mfa_secret(self, user) -> str | None:
        if not user.mfa_secret_id:
            return None
        try:
            return self.secrets.resolve(user.actor, user.mfa_secret_id).decode("ascii")
        except (KeyError, PermissionError, RuntimeError, UnicodeDecodeError, ValueError):
            return None

    def _own_mfa_setup(self, method, principal) -> APIResponse:
        if method != "POST":
            return self._method_not_allowed("POST")
        user = self.users.get(principal.user_id)
        if user.mfa_enabled:
            return APIResponse(
                409,
                {
                    "error": "multi-factor authentication is already enabled",
                    "code": "mfa_already_enabled",
                },
            )
        previous_secret = user.mfa_secret_id
        if previous_secret:
            self.users.set_mfa_state(user.id, None, False)
            try:
                self.secrets.delete(user.actor, previous_secret)
            except KeyError:
                pass

        secret = generate_totp_secret()
        metadata = self.secrets.create(
            user.actor,
            user.id,
            f"Account MFA {uuid.uuid4().hex[:10]}",
            "totp",
            secret,
        )
        user = self.users.set_mfa_state(user.id, metadata.id, False)
        self.audit.write(
            user.actor,
            "user.mfa.setup",
            "user",
            user.id,
            "success",
        )
        uri = provisioning_uri(user.username, secret)
        return APIResponse(
            200,
            {
                "user": self._user(user),
                "secret": secret,
                "provisioning_uri": uri,
                "qr_code": provisioning_qr_data_uri(uri),
            },
            (("Cache-Control", "no-store"),),
        )

    def _own_mfa(self, method, payload, principal) -> APIResponse:
        user = self.users.get(principal.user_id)
        if method == "PUT":
            data = self._object(payload, {"code"})
            secret = self._mfa_secret(user)
            if secret is None:
                return APIResponse(
                    409,
                    {
                        "error": "MFA setup must be started first",
                        "code": "mfa_setup_required",
                    },
                )
            if not verify_totp(secret, str(data.get("code") or "")):
                return APIResponse(
                    403,
                    {
                        "error": "authenticator code is invalid",
                        "code": "mfa_invalid",
                    },
                )
            user = self.users.set_mfa_state(user.id, user.mfa_secret_id, True)
            self.audit.write(
                user.actor,
                "user.mfa.enable",
                "user",
                user.id,
                "success",
            )
            return APIResponse(200, {"user": self._user(user)})

        if method == "DELETE":
            data = self._object(payload, {"password", "code"})
            authenticated = self.users.authenticate(
                principal.username,
                str(data.get("password") or ""),
            )
            if authenticated is None or authenticated.id != principal.user_id:
                return APIResponse(
                    403,
                    {"error": "current password is invalid", "code": "password_invalid"},
                )
            secret = self._mfa_secret(user)
            if not user.mfa_enabled or secret is None:
                return APIResponse(
                    409,
                    {
                        "error": "multi-factor authentication is not enabled",
                        "code": "mfa_not_enabled",
                    },
                )
            if not verify_totp(secret, str(data.get("code") or "")):
                return APIResponse(
                    403,
                    {
                        "error": "authenticator code is invalid",
                        "code": "mfa_invalid",
                    },
                )
            secret_id = user.mfa_secret_id
            user = self.users.set_mfa_state(user.id, None, False)
            if secret_id:
                try:
                    self.secrets.delete(user.actor, secret_id)
                except KeyError:
                    pass
            self.audit.write(
                user.actor,
                "user.mfa.disable",
                "user",
                user.id,
                "success",
            )
            return APIResponse(200, {"user": self._user(user)})

        return self._method_not_allowed("PUT, DELETE")

    def _email_overview_endpoint(self, method, actor) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        mailboxes = self.email_connections.store.list_mailboxes(actor)
        groups = self.email_connections.store.list_groups(actor)
        rules = self.email_connections.store.list_rules(actor)
        messages = self.email_connections.store.list_messages(actor, limit=25)
        processing = self.email_connections.store.list_processing(actor, limit=100)
        classifications = {
            "urgent": 0,
            "warning": 0,
            "information": 0,
            "ignore": 0,
        }
        for item in processing:
            if item.classification in classifications:
                classifications[item.classification] += 1
        return APIResponse(
            200,
            {
                "overview": {
                    "mailboxes": len(mailboxes),
                    "healthy_mailboxes": sum(
                        1
                        for item in mailboxes
                        if item.connection_state == "healthy" and item.enabled
                    ),
                    "groups": len(groups),
                    "enabled_groups": sum(1 for item in groups if item.enabled),
                    "rules": len(rules),
                    "enabled_rules": sum(1 for item in rules if item.enabled),
                    "recent_messages": len(messages),
                    "classifications": classifications,
                }
            },
        )

    def _email_groups_endpoint(self, method, payload, actor) -> APIResponse:
        store = self.email_connections.store
        if method == "GET":
            return APIResponse(
                200,
                {"groups": [self._email_group(item) for item in store.list_groups(actor)]},
            )
        if method == "POST":
            data = self._object(
                payload,
                {
                    "owner_user_id",
                    "name",
                    "description",
                    "enabled",
                    "quiet_window_seconds",
                },
            )
            owner_id = self._owner(data, actor)
            group = store.create_group(
                actor,
                owner_id,
                data.get("name"),
                description=str(data.get("description") or ""),
                enabled=self._boolean(data, "enabled", True),
                quiet_window_seconds=int(data.get("quiet_window_seconds") or 0),
            )
            self.audit.write(
                actor,
                "email.group.create",
                "email_group",
                group.id,
                "success",
                {"name": group.name},
            )
            return APIResponse(201, {"group": self._email_group(group)})
        return self._method_not_allowed("GET, POST")

    def _email_group_resource(
        self,
        method,
        payload,
        actor,
        group_id: str,
    ) -> APIResponse:
        store = self.email_connections.store
        if method == "GET":
            return APIResponse(
                200,
                {"group": self._email_group(store.get_group(actor, group_id))},
            )
        if method == "PATCH":
            data = self._object(
                payload,
                {
                    "name",
                    "description",
                    "enabled",
                    "quiet_window_seconds",
                },
            )
            group = store.update_group(
                actor,
                group_id,
                name=data.get("name") if "name" in data else None,
                description=(
                    str(data.get("description") or "")
                    if "description" in data
                    else None
                ),
                enabled=(
                    self._boolean(data, "enabled")
                    if "enabled" in data
                    else None
                ),
                quiet_window_seconds=(
                    int(data.get("quiet_window_seconds") or 0)
                    if "quiet_window_seconds" in data
                    else None
                ),
            )
            self.audit.write(
                actor,
                "email.group.update",
                "email_group",
                group.id,
                "success",
                {"name": group.name, "enabled": group.enabled},
            )
            return APIResponse(200, {"group": self._email_group(group)})
        if method == "DELETE":
            group = store.get_group(actor, group_id)
            store.delete_group(actor, group_id)
            self.audit.write(
                actor,
                "email.group.delete",
                "email_group",
                group_id,
                "success",
                {"name": group.name},
            )
            return APIResponse(204)
        return self._method_not_allowed("GET, PATCH, DELETE")

    def _email_rules_endpoint(self, method, payload, actor) -> APIResponse:
        store = self.email_connections.store
        if method == "GET":
            return APIResponse(
                200,
                {"rules": [self._email_rule(item) for item in store.list_rules(actor)]},
            )
        if method == "POST":
            data = self._object(
                payload,
                {
                    "owner_user_id",
                    "group_id",
                    "name",
                    "classification",
                    "conditions",
                    "match_mode",
                    "priority",
                    "enabled",
                },
            )
            owner_id = self._owner(data, actor)
            rule = store.create_rule(
                actor,
                owner_id,
                str(data.get("group_id") or ""),
                data.get("name"),
                data.get("classification"),
                data.get("conditions"),
                match_mode=str(data.get("match_mode") or "all"),
                priority=int(data.get("priority", 100)),
                enabled=self._boolean(data, "enabled", True),
            )
            self.audit.write(
                actor,
                "email.rule.create",
                "email_rule",
                rule.id,
                "success",
                {
                    "classification": rule.classification,
                    "match_mode": rule.match_mode,
                },
            )
            return APIResponse(201, {"rule": self._email_rule(rule)})
        return self._method_not_allowed("GET, POST")

    def _email_rule_resource(
        self,
        method,
        payload,
        actor,
        rule_id: str,
    ) -> APIResponse:
        store = self.email_connections.store
        if method == "GET":
            return APIResponse(
                200,
                {"rule": self._email_rule(store.get_rule(actor, rule_id))},
            )
        if method == "PATCH":
            data = self._object(
                payload,
                {
                    "group_id",
                    "name",
                    "classification",
                    "conditions",
                    "match_mode",
                    "priority",
                    "enabled",
                },
            )
            rule = store.update_rule(
                actor,
                rule_id,
                group_id=(
                    str(data.get("group_id") or "")
                    if "group_id" in data
                    else None
                ),
                name=data.get("name") if "name" in data else None,
                classification=(
                    data.get("classification")
                    if "classification" in data
                    else None
                ),
                conditions=(
                    data.get("conditions")
                    if "conditions" in data
                    else None
                ),
                match_mode=(
                    str(data.get("match_mode") or "")
                    if "match_mode" in data
                    else None
                ),
                priority=(
                    int(data.get("priority"))
                    if "priority" in data
                    else None
                ),
                enabled=(
                    self._boolean(data, "enabled")
                    if "enabled" in data
                    else None
                ),
            )
            self.audit.write(
                actor,
                "email.rule.update",
                "email_rule",
                rule.id,
                "success",
                {
                    "classification": rule.classification,
                    "match_mode": rule.match_mode,
                    "enabled": rule.enabled,
                },
            )
            return APIResponse(200, {"rule": self._email_rule(rule)})
        if method == "DELETE":
            rule = store.get_rule(actor, rule_id)
            store.delete_rule(actor, rule_id)
            self.audit.write(
                actor,
                "email.rule.delete",
                "email_rule",
                rule_id,
                "success",
                {"classification": rule.classification},
            )
            return APIResponse(204)
        return self._method_not_allowed("GET, PATCH, DELETE")

    def _email_rule_evaluate(self, method, payload, actor) -> APIResponse:
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"message_id", "body"})
        message_id = str(data.get("message_id") or "")
        if not _RESOURCE_ID.fullmatch(message_id):
            raise ValueError("message_id is invalid")
        body = str(data.get("body") or "")
        if len(body.encode("utf-8")) > 64 * 1024:
            raise ValueError("email rule evaluation body is too large")
        result = self.email_rules.evaluate_message(
            actor,
            message_id,
            body=body,
        )
        return APIResponse(200, {"evaluation": result.public()})

    def _email_activity_endpoint(self, method, actor) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        store = self.email_connections.store
        messages = store.list_activity_messages(actor, limit=100)
        processing = store.list_processing(actor, limit=250)
        latest = {}
        for item in processing:
            latest.setdefault(item.message_id, item)
        return APIResponse(
            200,
            {
                "messages": [
                    {
                        **self._email_message(item),
                        "processing": (
                            self._email_processing(latest[item.id])
                            if item.id in latest
                            else None
                        ),
                    }
                    for item in messages
                ],
                "processing": [
                    self._email_processing(item)
                    for item in processing
                ],
            },
        )

    def _email_oauth_complete(self, method, payload, actor) -> APIResponse:
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"code", "state"})
        mailbox = self.email_connections.oauth_complete_from_state(
            actor,
            code=str(data.get("code") or ""),
            state=str(data.get("state") or ""),
        )
        return APIResponse(
            200,
            {"mailbox": self._email_mailbox(mailbox)},
            (("Cache-Control", "no-store"),),
        )

    def _email_message_action(
        self,
        method,
        payload,
        actor,
        message_id: str,
        action: str,
    ) -> APIResponse:
        store = self.email_connections.store
        message = store.get_message(actor, message_id)

        if action == "preview":
            if method != "GET":
                return self._method_not_allowed("GET")
            preview = self.email_connections.preview_message(
                actor,
                message.id,
            )
            return APIResponse(
                200,
                {"preview": preview},
                (("Cache-Control", "no-store"),),
            )

        if method != "POST":
            return self._method_not_allowed("POST")

        if action == "reprocess":
            data = self._object(payload or {}, {"bypass_quiet_window"})
            bypass = self._boolean(
                data,
                "bypass_quiet_window",
                False,
            )
            result = self.email_pipeline.process(
                actor,
                message.id,
                replay=True,
                bypass_quiet_window=bypass,
            )
            return APIResponse(
                200,
                {"result": result.public()},
            )

        if action in {"mute-similar", "ignore-sender"}:
            self._object(payload or {}, set())
            rule = self._email_activity_ignore_rule(
                actor,
                message,
                action,
            )
            return APIResponse(
                201,
                {"rule": self._email_rule(rule)},
            )

        if action == "change-severity":
            data = self._object(payload, {"classification"})
            classification = str(
                data.get("classification") or ""
            ).strip().casefold()
            if classification not in {
                "urgent",
                "warning",
                "information",
            }:
                raise ValueError(
                    "classification must be urgent, warning, or information"
                )
            latest = store.latest_processing(actor, message.id)
            if latest is None or not latest.rule_id:
                raise ValueError(
                    "this Activity item does not have a matched rule to update"
                )
            rule = store.get_rule(actor, latest.rule_id)
            previous = rule.classification
            rule = store.update_rule(
                actor,
                rule.id,
                classification=classification,
            )
            self.audit.write(
                actor,
                "email.rule.change_severity",
                "email_rule",
                rule.id,
                "success",
                {
                    "message_id": message.id,
                    "previous": previous,
                    "classification": classification,
                },
            )
            return APIResponse(
                200,
                {"rule": self._email_rule(rule)},
            )

        return APIResponse(404, {"error": "resource not found"})

    def _email_activity_ignore_rule(
        self,
        actor,
        message,
        action: str,
    ):
        store = self.email_connections.store
        latest = store.latest_processing(actor, message.id)
        group = None
        if latest is not None and latest.group_id:
            try:
                candidate = store.get_group(actor, latest.group_id)
                if (
                    candidate.owner_user_id == message.owner_user_id
                    and candidate.enabled
                ):
                    group = candidate
            except KeyError:
                group = None
        if group is None:
            group = next(
                (
                    item
                    for item in store.list_groups(actor)
                    if item.owner_user_id == message.owner_user_id
                    and item.name.casefold() == "activity quick rules"
                    and item.enabled
                ),
                None,
            )
        if group is None:
            disabled_quick_group = next(
                (
                    item
                    for item in store.list_groups(actor)
                    if item.owner_user_id == message.owner_user_id
                    and item.name.casefold() == "activity quick rules"
                ),
                None,
            )
            if disabled_quick_group is not None:
                group = store.update_group(
                    actor,
                    disabled_quick_group.id,
                    enabled=True,
                )
        if group is None:
            group = store.create_group(
                actor,
                message.owner_user_id,
                "Activity quick rules",
                description=(
                    "Rules created from Email Alerts Activity quick actions."
                ),
            )

        if action == "ignore-sender":
            value = str(message.sender or "").strip().casefold()
            if not value:
                raise ValueError(
                    "this message does not have a sender to ignore"
                )
            condition = {
                "field": "sender",
                "operator": "equals",
                "value": value,
            }
            base_name = f"Ignore sender {value}"
            audit_action = "email.activity.ignore_sender"
        else:
            subject = re.sub(
                r"^(?:(?:re|fw|fwd)\s*:\s*)+",
                "",
                str(message.subject or ""),
                flags=re.IGNORECASE,
            )
            value = sanitize_text(subject)[:240]
            if not value:
                raise ValueError(
                    "this message does not have a subject to mute"
                )
            condition = {
                "field": "subject",
                "operator": "contains",
                "value": value,
            }
            base_name = f"Mute similar {value}"
            audit_action = "email.activity.mute_similar"

        name = self._email_unique_rule_name(
            actor,
            message.owner_user_id,
            group.id,
            base_name,
        )
        rule = store.create_rule(
            actor,
            message.owner_user_id,
            group.id,
            name,
            "ignore",
            [condition],
            match_mode="all",
            priority=0,
        )
        self.audit.write(
            actor,
            audit_action,
            "email_rule",
            rule.id,
            "success",
            {
                "message_id": message.id,
                "group_id": group.id,
                "condition_field": condition["field"],
            },
        )
        return rule

    def _email_unique_rule_name(
        self,
        actor,
        owner_user_id: str,
        group_id: str,
        base_name: str,
    ) -> str:
        compact = sanitize_text(base_name)[:140] or "Activity rule"
        existing = {
            item.name.casefold()
            for item in self.email_connections.store.list_rules(
                actor,
                group_id=group_id,
            )
            if item.owner_user_id == owner_user_id
        }
        if compact.casefold() not in existing:
            return compact
        for index in range(2, 100):
            suffix = f" {index}"
            candidate = compact[: 160 - len(suffix)] + suffix
            if candidate.casefold() not in existing:
                return candidate
        return (
            compact[:120]
            + " "
            + uuid.uuid4().hex[:8]
        )

    def _email_mailboxes_endpoint(self, method, payload, actor) -> APIResponse:
        if method == "GET":
            return APIResponse(
                200,
                {
                    "mailboxes": [
                        self._email_mailbox(item)
                        for item in self.email_connections.store.list_mailboxes(actor)
                    ]
                },
            )
        if method == "POST":
            data = self._object(
                payload,
                {
                    "owner_user_id",
                    "provider",
                    "address",
                    "name",
                    "settings",
                    "credential",
                    "enabled",
                },
            )
            owner_id = self._owner(data, actor)
            mailbox = self.email_connections.create_mailbox(
                actor,
                owner_id,
                data.get("provider"),
                data.get("address"),
                name=str(data.get("name") or ""),
                settings=data.get("settings", {}),
                credential=data.get("credential", {}),
                enabled=self._boolean(data, "enabled", True),
            )
            return APIResponse(
                201,
                {"mailbox": self._email_mailbox(mailbox)},
            )
        return self._method_not_allowed("GET, POST")

    def _email_mailbox_resource(
        self,
        method,
        payload,
        actor,
        mailbox_id: str,
        action: str | None,
    ) -> APIResponse:
        if action is None:
            if method == "GET":
                mailbox = self.email_connections.store.get_mailbox(
                    actor,
                    mailbox_id,
                )
                return APIResponse(
                    200,
                    {"mailbox": self._email_mailbox(mailbox)},
                )
            if method == "PATCH":
                data = self._object(
                    payload,
                    {"name", "settings", "enabled"},
                )
                mailbox = self.email_connections.update_mailbox(
                    actor,
                    mailbox_id,
                    name=data.get("name") if "name" in data else None,
                    settings=(
                        data.get("settings")
                        if "settings" in data
                        else None
                    ),
                    enabled=(
                        self._boolean(data, "enabled")
                        if "enabled" in data
                        else None
                    ),
                )
                return APIResponse(
                    200,
                    {"mailbox": self._email_mailbox(mailbox)},
                )
            if method == "DELETE":
                self.email_connections.delete_mailbox(actor, mailbox_id)
                return APIResponse(204)
            return self._method_not_allowed("GET, PATCH, DELETE")

        if action == "oauth-start":
            if method != "POST":
                return self._method_not_allowed("POST")
            self._object(payload or {}, set())
            result = self.email_connections.oauth_start(actor, mailbox_id)
            mailbox = self.email_connections.store.get_mailbox(
                actor,
                mailbox_id,
            )
            return APIResponse(
                200,
                {
                    "mailbox": self._email_mailbox(mailbox),
                    "oauth": result.public(),
                },
                (("Cache-Control", "no-store"),),
            )

        if action == "oauth-complete":
            if method != "POST":
                return self._method_not_allowed("POST")
            data = self._object(payload, {"code", "state"})
            mailbox = self.email_connections.oauth_complete(
                actor,
                mailbox_id,
                code=data.get("code"),
                state=data.get("state"),
            )
            return APIResponse(
                200,
                {"mailbox": self._email_mailbox(mailbox)},
                (("Cache-Control", "no-store"),),
            )

        if action == "sync":
            if method != "POST":
                return self._method_not_allowed("POST")
            self._object(payload or {}, set())
            summary = self.email_connections.sync_mailbox(
                actor,
                mailbox_id,
            )
            mailbox = self.email_connections.store.get_mailbox(
                actor,
                mailbox_id,
            )
            return APIResponse(
                200,
                {
                    "mailbox": self._email_mailbox(mailbox),
                    "sync": summary.public(),
                },
            )

        return APIResponse(404, {"error": "resource not found"})

    def _tokens_endpoint(self, method, payload, actor) -> APIResponse:
        if method == "GET":
            owner_id = actor.user_id
            tokens = [
                {
                    **self._token(item),
                    "management": "platform",
                    "enabled": item.enabled and item.revoked_at is None,
                    "credential_available": True,
                }
                for item in self.tokens.list_for_owner(actor, owner_id)
            ]
            if actor.is_admin and self.yaml_resource_authority:
                tokens.extend(self.configuration_sync.legacy_applications())
            return APIResponse(
                200,
                {"tokens": tokens},
            )
        if method == "POST":
            data = self._object(
                payload,
                {
                    "owner_user_id",
                    "name",
                    "source_scopes",
                    "role",
                    "rate_limit_per_minute",
                    "expires_at",
                },
            )
            owner_id = self._owner(data, actor)
            credentials = self.tokens.create(
                actor,
                owner_id,
                data.get("name"),
                source_scopes=data.get("source_scopes", []),
                role=data.get("role", "application"),
                rate_limit_per_minute=data.get("rate_limit_per_minute", 60),
                expires_at=data.get("expires_at"),
            )
            return APIResponse(
                201,
                {"token": self._token(credentials.token), "value": credentials.value},
                (("Cache-Control", "no-store"),),
            )
        return self._method_not_allowed("GET, POST")

    def _destinations_endpoint(self, method, payload, actor) -> APIResponse:
        if self.yaml_resource_authority:
            if method == "GET":
                return APIResponse(
                    200,
                    {
                        "destinations": [
                            {**self._destination(item), "management": "yaml"}
                            for item in self.configuration_sync.list_destinations(actor)
                        ]
                    },
                )
            self._require_admin(actor)
            if method == "POST":
                data = self._object(
                    payload,
                    {"name", "output_type", "settings", "shared", "enabled", "secret"},
                )
                destination = self.configuration_sync.create_destination(actor, data)
                return APIResponse(
                    201,
                    {"destination": {**self._destination(destination), "management": "yaml"}},
                )
            return self._method_not_allowed("GET, POST")
        if method == "GET":
            destinations, errors = self.destinations.list_visible_safe(actor)
            return APIResponse(
                200,
                {
                    "destinations": [self._destination(item) for item in destinations],
                    "errors": errors,
                },
            )
        if method == "POST":
            data = self._object(
                payload,
                {
                    "owner_user_id",
                    "name",
                    "output_type",
                    "settings",
                    "shared",
                    "enabled",
                    "secret",
                },
            )
            owner_id = self._owner(data, actor)
            output_type = data.get("output_type")
            settings = data.get("settings", {})
            normalized_settings = normalize_output_settings(output_type, settings)
            if (
                str(output_type or "").strip().casefold() == "email"
                and normalized_settings.get("username")
                and not self._email_password_configured(data.get("secret"))
            ):
                raise ValueError(
                    "Email destination password is required when username is configured"
                )
            if not self.destinations.name_available(owner_id, data.get("name")):
                raise ConflictError(
                    f"A destination named {str(data.get('name') or '').strip()} already exists."
                )
            secret_value = (
                self._secret_value(data.get("secret"))
                if "secret" in data
                else None
            )
            destination = self.destinations.create(
                actor,
                owner_id,
                data.get("name"),
                output_type,
                settings=settings,
                shared=self._boolean(data, "shared", False),
                enabled=self._boolean(data, "enabled", True),
            )
            if secret_value is not None:
                destination_actor = (
                    actor
                    if owner_id == actor.user_id
                    else Actor(owner_id, "user")
                )
                try:
                    secret = self.secrets.create(
                        actor,
                        owner_id,
                        self._secret_name(destination.name),
                        f"{destination.output_type}-credentials",
                        secret_value,
                    )
                    destination = self.destinations.set_secret(
                        destination_actor,
                        destination.id,
                        secret.id,
                    )
                except Exception:
                    self.destinations.delete(destination_actor, destination.id)
                    raise
            return APIResponse(201, {"destination": self._destination(destination)})
        return self._method_not_allowed("GET, POST")

    def _routes_endpoint(self, method, payload, actor) -> APIResponse:
        if self.yaml_resource_authority:
            if method == "GET":
                return APIResponse(
                    200,
                    {
                        "routes": [
                            {**self._route(item), "management": "yaml"}
                            for item in self.configuration_sync.list_routes(actor)
                        ]
                    },
                )
            self._require_admin(actor)
            if method == "POST":
                data = self._object(
                    payload,
                    {
                        "name",
                        "source",
                        "input_type",
                        "destination_id",
                        "filters",
                        "priority",
                        "enabled",
                    },
                )
                route = self.configuration_sync.create_route(actor, data)
                return APIResponse(
                    201,
                    {"route": {**self._route(route), "management": "yaml"}},
                )
            return self._method_not_allowed("GET, POST")
        if method == "GET":
            routes, errors = self.routes.list_visible_safe(actor)
            return APIResponse(
                200,
                {"routes": [self._route(item) for item in routes], "errors": errors},
            )
        if method == "POST":
            data = self._object(
                payload,
                {
                    "owner_user_id",
                    "name",
                    "source",
                    "input_type",
                    "destination_id",
                    "filters",
                    "priority",
                    "enabled",
                },
            )
            route = self.routes.create(
                actor,
                self._owner(data, actor),
                data.get("name"),
                data.get("source"),
                data.get("destination_id"),
                input_type=data.get("input_type", ""),
                filters=data.get("filters", {}),
                priority=data.get("priority", 100),
                enabled=self._boolean(data, "enabled", True),
            )
            return APIResponse(201, {"route": self._route(route)})
        return self._method_not_allowed("GET, POST")

    def _deliveries_endpoint(self, method, actor) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        attempts = self.history.list_visible(actor, limit=100)
        return APIResponse(200, {"deliveries": [self._delivery(item) for item in attempts]})

    _DELIVERY_PAGE_SIZES = (25, 50, 100, 150, 250, 500)

    def _deliveries_page_endpoint(self, method, actor, page, size=None) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        page_size = 25
        if size is not None and int(size) in self._DELIVERY_PAGE_SIZES:
            page_size = int(size)
        total = self.history.count_visible(actor)
        total_pages = max(1, (total + page_size - 1) // page_size)
        current = min(max(1, int(page)), total_pages)
        attempts = self.history.list_visible(
            actor,
            limit=page_size,
            offset=(current - 1) * page_size,
        )
        return APIResponse(
            200,
            {
                "deliveries": [self._delivery(item) for item in attempts],
                "pagination": {
                    "page": current,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                },
            },
        )

    def _metrics_endpoint(self, method, actor, history_range) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        windows = {
            "10m": 10 * 60,
            "1h": 60 * 60,
            "1d": 24 * 60 * 60,
            "1m": 31 * 24 * 60 * 60,
            "1y": 366 * 24 * 60 * 60,
        }
        if history_range not in windows:
            raise ValueError("history range is invalid")
        since = int(time.time()) - windows[history_range]
        delivery = self.history.metrics(actor, since)
        with self.database.connect() as connection:
            route_where = "WHERE routes.enabled = 1"
            destination_where = "WHERE enabled = 1"
            parameters = ()
            if not actor.is_admin:
                route_where += " AND (routes.owner_user_id = ? OR routes.destination_id IN (SELECT id FROM destinations WHERE shared = 1))"
                destination_where += " AND (owner_user_id = ? OR shared = 1)"
                parameters = (actor.user_id,)
            route_row = connection.execute(
                f"SELECT COUNT(*) AS total, COUNT(DISTINCT source) AS sources FROM routes {route_where}",
                parameters,
            ).fetchone()
            destination_row = connection.execute(
                f"SELECT COUNT(*) FROM destinations {destination_where}",
                parameters,
            ).fetchone()
        applications = self.tokens.list_for_owner(actor, actor.user_id)
        active_applications = sum(
            1 for item in applications
            if item.enabled and item.revoked_at is None
        )
        if actor.is_admin and self.configuration_sync is not None:
            active_applications += sum(
                1 for item in self.configuration_sync.legacy_applications()
                if item["enabled"] and item["credential_available"]
            )
        return APIResponse(
            200,
            {
                "metrics": {
                    "range": history_range,
                    "since": since,
                    "sources": int(route_row["sources"] or 0),
                    "destinations": int(destination_row[0] or 0),
                    "routes": int(route_row["total"] or 0),
                    "applications": active_applications,
                    **delivery,
                }
            },
        )

    def _audit_endpoint(self, method, actor) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        events = self.audit.list_visible(actor, limit=500)
        return APIResponse(200, {"audit_events": self._audit_items(events)})

    _AUDIT_PAGE_SIZES = (25, 50, 100, 150, 250, 500)

    def _audit_page_endpoint(self, method, actor, page, size=None) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        page_size = 25
        if size is not None and int(size) in self._AUDIT_PAGE_SIZES:
            page_size = int(size)
        total = self.audit.count_visible(actor)
        total_pages = max(1, (total + page_size - 1) // page_size)
        current = min(max(1, int(page)), total_pages)
        events = self.audit.list_visible(
            actor,
            limit=page_size,
            offset=(current - 1) * page_size,
        )
        return APIResponse(
            200,
            {
                "audit_events": self._audit_items(events),
                "pagination": {
                    "page": current,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                },
            },
        )

    def _health_endpoint(self, method, actor) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        checks = self.health.run()
        self.audit.write(
            actor,
            "health.check",
            "platform",
            None,
            "success" if all(item["status"] == "healthy" for item in checks) else "warning",
            {"checks": len(checks)},
        )
        return APIResponse(200, {"checks": checks})

    def _housekeeping_endpoint(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if method == "GET":
            return APIResponse(
                200,
                {
                    "settings": self.housekeeping.settings(),
                    "status": self.housekeeping.status(),
                },
            )
        if method == "PUT":
            data = self._object(
                payload,
                {
                    "enabled",
                    "time",
                    "delivery_history_days",
                    "audit_history_days",
                    "backup_run_history_days",
                },
            )
            required = {
                "enabled",
                "time",
                "delivery_history_days",
                "audit_history_days",
                "backup_run_history_days",
            }
            if set(data) != required:
                raise ValueError("every housekeeping setting is required")
            settings = self.housekeeping.update_settings(actor, data)
            return APIResponse(
                200,
                {"settings": settings, "status": self.housekeeping.status()},
            )
        return self._method_not_allowed("GET, PUT")

    def _backup_settings_endpoint(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if self.configuration_sync is None:
            return APIResponse(404, {"error": "resource not found"})
        if method == "GET":
            return APIResponse(
                200,
                {
                    "settings": self.configuration_sync.backup_settings(),
                    "last_run": self.backup_scheduler.last_run(),
                },
            )
        if method == "PUT":
            data = self._object(
                payload,
                {
                    "schedule", "time", "weekday", "day",
                    "external_enabled", "external_type", "external_path",
                    "target_id", "managed_mounts",
                },
            )
            target_id = str(data.get("target_id") or "")
            if target_id:
                self.backup_targets.get(actor, target_id)
            settings = self.configuration_sync.update_backup_settings(actor, data)
            return APIResponse(200, {"settings": settings})
        return self._method_not_allowed("GET, PUT")

    def _backup_targets_endpoint(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if method == "GET":
            return APIResponse(
                200,
                {
                    "targets": [item.public() for item in self.backup_targets.list(actor)],
                    "managed_mounts": self.backup_targets.managed_mounts,
                },
            )
        if method == "POST":
            data = self._object(
                payload,
                {
                    "name", "type", "host", "remote_path", "share_name",
                    "local_path", "username", "domain", "password",
                    "mount_options", "enabled",
                },
            )
            target = self.backup_targets.create(actor, data)
            self.audit.write(
                actor, "backup.target.create", "backup_target", target.id,
                "success", {"name": target.name, "type": target.target_type},
            )
            return APIResponse(201, {"target": target.public()})
        return self._method_not_allowed("GET, POST")

    def _backup_run_endpoint(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"target_id"})
        target_id = str(data.get("target_id") or "")
        if target_id:
            self.backup_targets.get(actor, target_id)
        result = self.backup_scheduler.run_now(actor, target_id or None)
        self.audit.write(
            actor, "backup.run", "backup", result.get("backup_id"),
            result["outcome"], {"target_id": target_id or "local-state"},
        )
        return APIResponse(201, {"run": result})

    def _reboot_endpoint(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"reason"})
        reason = sanitize_text(data.get("reason") or "").strip()
        if not 3 <= len(reason) <= 500:
            raise ValueError("restart reason must contain 3 to 500 characters")
        self.audit.write(
            actor, "platform.restart", "platform", None, "accepted",
            {"reason": reason},
        )
        timer = threading.Timer(0.35, self.reboot_callback)
        timer.daemon = True
        timer.start()
        return APIResponse(202, {"status": "restarting"})

    def _portability_export(self, method, actor) -> APIResponse:
        self._require_admin(actor)
        if method != "GET":
            return self._method_not_allowed("GET")
        return APIResponse(200, {"document": self.portability.export_document(actor)})

    def _portability_preview(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"document"})
        if "document" not in data:
            raise ValueError("document is required")
        plan = self.portability.preview_document(actor, data["document"])
        return APIResponse(200, {"preview": plan.public()})

    def _portability_import(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"document", "fingerprint", "confirm"})
        if self._boolean(data, "confirm") is not True:
            raise ValueError("confirmed import is required")
        result = self.portability.apply_document(
            actor,
            data.get("document"),
            str(data.get("fingerprint") or ""),
        )
        if self.configuration_sync is not None:
            result["yaml_resources_adopted"] = self.configuration_sync.adopt_unmanaged_resources(actor)
        return APIResponse(200, {"import": result})

    def _v1_migration_preview(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"yaml"})
        plan = self.portability.preview_v1_yaml(actor, data.get("yaml"))
        return APIResponse(200, {"preview": plan.public()})

    def _v1_migration_import(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"yaml", "fingerprint", "confirm"})
        if self._boolean(data, "confirm") is not True:
            raise ValueError("confirmed migration is required")
        result = self.portability.apply_v1_yaml(
            actor,
            data.get("yaml"),
            str(data.get("fingerprint") or ""),
        )
        if self.configuration_sync is not None:
            result["yaml_resources_adopted"] = self.configuration_sync.adopt_unmanaged_resources(actor)
        return APIResponse(200, {"import": result})

    def _configuration_inventory(self, method, actor) -> APIResponse:
        self._require_admin(actor)
        if method != "GET":
            return self._method_not_allowed("GET")
        bridge = self._configuration_bridge()
        configuration = bridge.inventory(actor)
        if self.configuration_sync is not None:
            status = self.configuration_sync.synchronize()
            configuration["sync"] = {
                "ready": status.ready,
                "changed": status.changed,
                "errors": list(status.errors),
                "fingerprint": status.fingerprint,
            }
            with self.database.connect() as connection:
                destination_count = int(
                    connection.execute("SELECT COUNT(*) FROM destinations").fetchone()[0]
                )
                route_count = int(
                    connection.execute("SELECT COUNT(*) FROM routes").fetchone()[0]
                )
                token_count = int(
                    connection.execute("SELECT COUNT(*) FROM api_tokens").fetchone()[0]
                )
            configuration["applications"] = []
            configuration["preferences"] = self.configuration_sync.preferences()
            configuration["authority"] = (
                "database" if self.configuration_sync.database_authoritative else "yaml"
            )
            configuration["resource_model"] = (
                "platform_database_v1"
                if self.configuration_sync.database_authoritative
                else "unified_yaml_v1"
            )
            configuration["migration_available"] = not self.configuration_sync.database_authoritative
            configuration["summary"]["outputs"] = destination_count
            configuration["summary"]["routes"] = route_count
            configuration["summary"]["applications"] = token_count
        return APIResponse(
            200,
            {"configuration": configuration},
            (("Cache-Control", "no-store"),),
        )

    def _integrations_endpoint(self, method, payload, actor) -> APIResponse:
        overrides = self.integration_categories.list_overrides()
        if method == "GET":
            return APIResponse(
                200,
                {
                    "integrations": integrations(overrides),
                    "route_options": route_options(overrides),
                },
            )
        if method == "PUT":
            self._require_admin(actor)
            data = self._object(payload, {"source", "category"})
            if set(data) != {"source", "category"}:
                raise ValueError("integration and category are required")
            self.integration_categories.set_category(
                data.get("source"),
                data.get("category"),
            )
            self.audit.write(
                actor,
                "integration.category.update",
                "integration",
                str(data.get("source") or ""),
                "success",
                {"category": str(data.get("category") or "")},
            )
            overrides = self.integration_categories.list_overrides()
            return APIResponse(
                200,
                {
                    "integrations": integrations(overrides),
                    "route_options": route_options(overrides),
                },
            )
        return self._method_not_allowed("GET, PUT")

    def _integration_settings_endpoint(
        self,
        method,
        payload,
        actor,
    ) -> APIResponse:
        if self.configuration_sync is None:
            return APIResponse(404, {"error": "resource not found"})
        if method != "GET":
            return self._method_not_allowed("GET")
        result = self.configuration_sync.integration_settings()
        return APIResponse(200, result)

    def _integration_settings_resource(
        self,
        method,
        payload,
        actor,
        source,
    ) -> APIResponse:
        if self.configuration_sync is None:
            return APIResponse(404, {"error": "resource not found"})
        key = str(source or "").strip().casefold()
        current = self.configuration_sync.integration_settings()
        if key not in current["settings"]:
            raise KeyError("integration settings not found")
        if method == "GET":
            errors = [
                item
                for item in current["errors"]
                if item.get("resource") == key
            ]
            return APIResponse(
                200,
                {"source": key, "settings": current["settings"][key], "errors": errors},
            )
        if method == "PUT":
            self._require_admin(actor)
            data = self._object(payload, set(current["settings"][key]))
            settings = self.configuration_sync.update_integration_settings(
                actor,
                key,
                data,
            )
            return APIResponse(200, {"source": key, "settings": settings})
        return self._method_not_allowed("GET, PUT")

    def _preferences_endpoint(self, method, payload, actor) -> APIResponse:
        if self.configuration_sync is None:
            return APIResponse(404, {"error": "resource not found"})
        if method == "GET":
            return APIResponse(200, {"preferences": self.configuration_sync.preferences()})
        if method == "PUT":
            self._require_admin(actor)
            data = self._object(payload, {"timezone", "language", "time_format"})
            if set(data) != {"timezone", "language", "time_format"}:
                raise ValueError("every preference is required")
            return APIResponse(
                200,
                {"preferences": self.configuration_sync.update_preferences(actor, data)},
            )
        return self._method_not_allowed("GET, PUT")

    def _source_categories_endpoint(self, method, payload, actor) -> APIResponse:
        if method == "GET":
            return APIResponse(
                200,
                {
                    "categories": self.integration_categories.list_overrides(),
                    "removed_sources": [],
                },
            )
        if method == "PUT":
            data = self._object(payload, {"source", "category"})
            response = self._integrations_endpoint(method, data, actor)
            if response.status == 200:
                return APIResponse(
                    200,
                    {
                        "categories": self.integration_categories.list_overrides(),
                        "removed_sources": [],
                    },
                )
            return response
        if method == "DELETE":
            raise ValueError("built-in integrations cannot be removed")
        return self._method_not_allowed("GET, PUT")

    def _version_endpoint(self, method) -> APIResponse:
        if method != "GET":
            return self._method_not_allowed("GET")
        available = str(
            compatible_environment("NOWLERT_AVAILABLE_VERSION", default="") or ""
        ).strip()
        return APIResponse(
            200,
            {
                "version": {
                    "running": VERSION,
                    "available": available,
                    "update_available": bool(
                        available
                        and self._version_key(available) > self._version_key(VERSION)
                    ),
                }
            },
        )

    def _configuration_migration_preview(self, method, actor) -> APIResponse:
        self._require_admin(actor)
        if self.configuration_sync is not None:
            raise ValueError("routing-authority migration is retired by database-authoritative resources")
        if method != "POST":
            return self._method_not_allowed("POST")
        plan, inventory, warnings = self._configuration_bridge().preview(actor)
        public = plan.public()
        public["warnings"] = list(warnings)
        public["inventory"] = inventory["summary"]
        public["current_authority"] = inventory["authority"]
        return APIResponse(
            200,
            {"preview": public},
            (("Cache-Control", "no-store"),),
        )

    def _configuration_migration_apply(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if self.configuration_sync is not None:
            raise ValueError("routing-authority migration is retired by database-authoritative resources")
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"fingerprint", "confirm"})
        if self._boolean(data, "confirm") is not True:
            raise ValueError("confirmed migration is required")
        result = self._configuration_bridge().activate(
            actor,
            str(data.get("fingerprint") or ""),
        )
        return APIResponse(200, {"migration": result})

    def _configuration_authority(self, method, payload, actor) -> APIResponse:
        self._require_admin(actor)
        if self.configuration_sync is not None:
            raise ValueError("routing authority is fixed to database-authoritative resources")
        if method != "PUT":
            return self._method_not_allowed("PUT")
        data = self._object(payload, {"authority", "confirmation"})
        result = self._configuration_bridge().set_authority(
            actor,
            str(data.get("authority") or ""),
            str(data.get("confirmation") or ""),
        )
        return APIResponse(200, {"routing": result})

    def _configuration_bridge(self) -> ConfigurationBridgeService:
        if self.configuration_bridge is None:
            raise RuntimeError("mounted configuration bridge is unavailable")
        return self.configuration_bridge

    def _backup_public(self, item) -> dict:
        payload = item.public()
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT period_key FROM backup_schedule_runs
                WHERE backup_id = ?
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (item.id,),
            ).fetchone()
        period = str(row["period_key"]) if row is not None else ""
        payload["backup_type"] = (
            "scheduled"
            if period.startswith(("daily:", "weekly:", "monthly:"))
            else "manual"
        )
        return payload

    def _backups_endpoint(self, method, actor) -> APIResponse:
        self._require_admin(actor)
        if method == "GET":
            return APIResponse(
                200,
                {"backups": [self._backup_public(item) for item in self.backups.list(actor)]},
            )
        if method == "POST":
            backup = self.backups.create(actor)
            return APIResponse(201, {"backup": self._backup_public(backup)})
        return self._method_not_allowed("GET, POST")

    def _resource_endpoint(self, method, path, payload, actor):
        metrics_match = re.fullmatch(r"/api/v2/metrics/(10m|1h|1d|1m|1y)", path)
        if metrics_match:
            return self._metrics_endpoint(method, actor, metrics_match.group(1))

        external_restore_match = re.fullmatch(
            r"/api/v2/backup-targets/([0-9a-f]{32})/backups/"
            r"(state-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8})/restore",
            path,
        )
        if external_restore_match:
            self._require_admin(actor)
            if method != "POST":
                return self._method_not_allowed("POST")
            target_id, backup_id = external_restore_match.groups()
            data = self._object(payload, {"confirmation"})
            target = self.backup_targets.get(actor, target_id)
            destination = self.backup_targets.ensure_ready(actor, target)
            result = self.backups.restore_external(
                actor,
                backup_id,
                str(data.get("confirmation") or ""),
                destination,
            )
            result["restart_scheduled"] = self._schedule_restore_restart()
            return APIResponse(200, {"restore": result}, self._clear_cookies())

        external_list_match = re.fullmatch(
            r"/api/v2/backup-targets/([0-9a-f]{32})/backups",
            path,
        )
        if external_list_match:
            self._require_admin(actor)
            if method != "GET":
                return self._method_not_allowed("GET")
            target = self.backup_targets.get(actor, external_list_match.group(1))
            destination = self.backup_targets.ensure_ready(actor, target)
            backups = self.backups.list_external(actor, destination)
            return APIResponse(
                200,
                {
                    "target": target.public(),
                    "backups": [self._backup_public(item) for item in backups],
                },
            )

        target_match = re.fullmatch(
            r"/api/v2/backup-targets/([0-9a-f]{32})(?:/(test))?", path
        )
        if target_match:
            self._require_admin(actor)
            target_id, action = target_match.groups()
            if action == "test":
                if method != "POST":
                    return self._method_not_allowed("POST")
                target = self.backup_targets.test(actor, target_id)
                self.audit.write(
                    actor, "backup.target.test", "backup_target", target.id,
                    target.last_test_outcome or "failed",
                    {"name": target.name, "type": target.target_type},
                )
                return APIResponse(200, {"target": target.public()})
            if method == "GET":
                return APIResponse(
                    200, {"target": self.backup_targets.get(actor, target_id).public()}
                )
            if method == "PATCH":
                data = self._object(
                    payload,
                    {
                        "name", "type", "host", "remote_path", "share_name",
                        "local_path", "username", "domain", "password",
                        "mount_options", "enabled",
                    },
                )
                target = self.backup_targets.update(actor, target_id, data)
                self.audit.write(
                    actor, "backup.target.update", "backup_target", target.id,
                    "success", {"name": target.name, "type": target.target_type},
                )
                return APIResponse(200, {"target": target.public()})
            if method == "DELETE":
                self.backup_targets.delete(actor, target_id)
                self.audit.write(
                    actor, "backup.target.delete", "backup_target", target_id,
                    "success",
                )
                return APIResponse(204)
            return self._method_not_allowed("GET, PATCH, DELETE")

        input_match = re.fullmatch(
            r"/api/v2/configuration/inputs/(smtp|http|redfish)",
            path,
        )
        if input_match:
            if method != "PATCH":
                return self._method_not_allowed("PATCH")
            self._require_admin(actor)
            data = self._object(payload, {"enabled"})
            if "enabled" not in data or self.configuration_sync is None:
                raise ValueError("enabled is required")
            result = self.configuration_sync.update_input(
                actor,
                input_match.group(1),
                self._boolean(data, "enabled"),
            )
            return APIResponse(200, {"input": result})

        backup_match = re.fullmatch(
            r"/api/v2/backups/(state-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8})(?:/(restore))?",
            path,
        )
        if backup_match:
            backup_id, action = backup_match.groups()

            if action == "restore":
                return self._backup_restore(
                    method,
                    payload,
                    actor,
                    backup_id,
                )

            self._require_admin(actor)

            if method != "DELETE":
                return self._method_not_allowed("DELETE")

            self.backups.delete(actor, backup_id)
            return APIResponse(204)

        user_match = re.fullmatch(
            r"/api/v2/users/([0-9a-f]{32})(?:/(password|tokens|routes))?",
            path,
        )
        if user_match:
            return self._user_resource(method, payload, actor, *user_match.groups())

        token_match = re.fullmatch(
            r"/api/v2/tokens/((?:[0-9a-f]{32})|(?:yaml-[0-9a-f]{24}))(?:/(rotate|revoke))?",
            path,
        )
        if token_match:
            return self._token_resource(method, payload, actor, *token_match.groups())

        destination_match = re.fullmatch(
            r"/api/v2/destinations/([0-9a-f]{32})(?:/(preview|test))?",
            path,
        )
        if destination_match:
            return self._destination_resource(
                method,
                payload,
                actor,
                *destination_match.groups(),
            )

        route_match = re.fullmatch(r"/api/v2/routes/([0-9a-f]{32})", path)
        if route_match:
            return self._route_resource(method, payload, actor, route_match.group(1))
        return None

    def _backup_restore(self, method, payload, actor, backup_id):
        self._require_admin(actor)
        if method != "POST":
            return self._method_not_allowed("POST")
        data = self._object(payload, {"confirmation"})
        result = self.backups.restore(
            actor,
            backup_id,
            str(data.get("confirmation") or ""),
        )
        result["restart_scheduled"] = self._schedule_restore_restart()
        return APIResponse(200, {"restore": result}, self._clear_cookies())

    def _schedule_restore_restart(self) -> bool:
        if not callable(getattr(self.configuration, "reload", None)):
            return False
        timer = threading.Timer(0.75, self.reboot_callback)
        timer.daemon = True
        timer.start()
        return True

    def _user_resource(self, method, payload, actor, user_id, action):
        self._require_admin(actor)
        if action == "tokens":
            if method != "GET":
                return self._method_not_allowed("GET")
            tokens = self.tokens.list_for_owner(actor, user_id)
            return APIResponse(200, {"tokens": [self._token(item) for item in tokens]})
        if action == "routes":
            if method != "GET":
                return self._method_not_allowed("GET")
            routes = self.routes.list_for_owner(actor, user_id)
            return APIResponse(200, {"routes": [self._route(item) for item in routes]})
        if action == "password":
            if method != "PUT":
                return self._method_not_allowed("PUT")
            if user_id == actor.user_id:
                raise PermissionError(
                    "the current account must change its password from Account security"
                )
            data = self._object(payload, {"password"})
            user = self.users.reset_password(user_id, data.get("password"))
            self.audit.write(actor, "user.password", "user", user.id, "success")
            return APIResponse(200, {"user": self._user(user)})
        if method == "GET":
            return APIResponse(200, {"user": self._user(self.users.get(user_id))})
        if method == "PATCH":
            data = self._object(payload, {"enabled"})
            if "enabled" not in data:
                raise ValueError("enabled is required")
            user = self.users.set_enabled(user_id, self._boolean(data, "enabled"))
            self.audit.write(
                actor,
                "user.enable" if user.enabled else "user.disable",
                "user",
                user.id,
                "success",
            )
            return APIResponse(200, {"user": self._user(user)})
        if method == "DELETE":
            if user_id == actor.user_id:
                raise PermissionError(
                    "the current administrator cannot delete its own account"
                )

            user = self.users.get(user_id)
            self.users.delete(user_id)
            self.audit.write(
                actor,
                "user.delete",
                "user",
                user.id,
                "success",
                {
                    "username": user.username,
                    "role": user.role,
                },
            )
            return APIResponse(204)
        return self._method_not_allowed("GET, PATCH, DELETE")

    def _token_resource(self, method, payload, actor, token_id, action):
        if action is None:
            if method == "PATCH":
                data = self._object(payload, {"enabled"})
                if "enabled" not in data:
                    raise ValueError("enabled is required")
                enabled = self._boolean(data, "enabled")
                if token_id.startswith("yaml-"):
                    if not self.yaml_resource_authority:
                        raise KeyError("application not found")
                    token = self.configuration_sync.update_application(
                        actor, token_id, enabled=enabled
                    )
                    return APIResponse(200, {"token": token})
                token = self.tokens.set_enabled(actor, token_id, enabled)
                return APIResponse(200, {"token": self._token(token)})
            if method == "DELETE":
                if token_id.startswith("yaml-"):
                    if not self.yaml_resource_authority:
                        raise KeyError("application not found")
                    self.configuration_sync.delete_application(actor, token_id)
                else:
                    self.tokens.delete(actor, token_id)
                return APIResponse(204)
            return self._method_not_allowed("PATCH, DELETE")
        if method != "POST" or token_id.startswith("yaml-"):
            return self._method_not_allowed("POST")
        if action == "rotate":
            credentials = self.tokens.rotate(actor, token_id)
            return APIResponse(
                200,
                {"token": self._token(credentials.token), "value": credentials.value},
                (("Cache-Control", "no-store"),),
            )
        token = self.tokens.revoke(actor, token_id)
        return APIResponse(200, {"token": self._token(token)})

    def _destination_resource(self, method, payload, actor, destination_id, action):
        if action in {"preview", "test"}:
            if method != "POST":
                return self._method_not_allowed("POST")
            if action == "test" and self.yaml_resource_authority:
                self._require_admin(actor)
            data = self._object(payload, {"event", "message_style"})
            notification = self._notification(data.get("event"))
            message_style = data.get("message_style")
            if action == "preview":
                preview = self.outputs.preview(
                    actor,
                    destination_id,
                    notification,
                    message_style=message_style,
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
                message_style=message_style,
            )
            response = {
                "result": self._delivery_result(result),
            }
            try:
                destination = self.destinations.get(actor, destination_id)
            except (KeyError, PermissionError):
                destination = None
            if destination is not None:
                response["destination"] = self._destination(destination)
            return APIResponse(200, response)

        if method == "GET":
            if self.yaml_resource_authority:
                item = next(
                    (
                        value
                        for value in self.configuration_sync.list_destinations(actor)
                        if value.id == destination_id
                    ),
                    None,
                )
                if item is None:
                    raise KeyError("destination not found")
                return APIResponse(200, {"destination": {**self._destination(item), "management": "yaml"}})
            destination = self.destinations.get(actor, destination_id)
            return APIResponse(200, {"destination": self._destination(destination)})
        if method == "PATCH":
            data = self._object(payload, {"name", "output_type", "settings", "enabled", "shared", "secret"})
            if self.yaml_resource_authority:
                destination = self.configuration_sync.update_destination(actor, destination_id, data)
                return APIResponse(
                    200,
                    {"destination": {**self._destination(destination), "management": "yaml"}},
                )
            destination = self.destinations.get(actor, destination_id)
            if destination.owner_user_id != actor.user_id:
                raise PermissionError("destination cannot be changed by this user")

            next_name = data.get("name", destination.name)
            next_type = str(
                data.get("output_type", destination.output_type)
                or destination.output_type
            ).strip().casefold()
            type_changed = next_type != destination.output_type
            if not self.destinations.name_available(
                destination.owner_user_id,
                next_name,
                excluding_id=destination.id,
            ):
                raise ConflictError(
                    f"A destination named {str(next_name or '').strip()} already exists."
                )
            if type_changed and "settings" not in data:
                raise ValueError(
                    "destination settings are required when changing destination type"
                )
            if type_changed and "secret" not in data:
                raise ValueError(
                    "new credentials are required when changing destination type"
                )
            next_settings = data.get("settings", destination.settings)
            normalized_settings = normalize_output_settings(
                next_type,
                next_settings,
            )
            if (
                next_type == "email"
                and normalized_settings.get("username")
                and (
                    ("secret" in data and not self._email_password_configured(data.get("secret")))
                    or ("secret" not in data and not destination.secret_configured)
                )
            ):
                raise ValueError(
                    "Email destination password is required when username is configured"
                )
            enabled = (
                self._boolean(data, "enabled")
                if "enabled" in data
                else destination.enabled
            )
            shared = (
                self._boolean(data, "shared")
                if "shared" in data
                else destination.shared
            )
            secret_value = (
                self._secret_value(data.get("secret"))
                if "secret" in data
                else None
            )

            if secret_value is not None:
                target = self.destinations.for_delivery_metadata(actor, destination_id)
                if target.secret_id:
                    self.secrets.rotate(actor, target.secret_id, secret_value)
                else:
                    secret = self.secrets.create(
                        actor,
                        target.destination.owner_user_id,
                        self._secret_name(str(next_name)),
                        f"{next_type}-credentials",
                        secret_value,
                    )
                    self.destinations.set_secret(actor, destination_id, secret.id)

            destination = self.destinations.update(
                actor,
                destination_id,
                name=next_name,
                output_type=next_type,
                settings=next_settings,
                enabled=enabled,
                shared=shared,
            )
            return APIResponse(200, {"destination": self._destination(destination)})
        if method == "DELETE":
            if self.yaml_resource_authority:
                self.configuration_sync.delete_destination(actor, destination_id)
                return APIResponse(204)
            destination = self.destinations.get(actor, destination_id)
            if destination.owner_user_id != actor.user_id:
                raise PermissionError("destination cannot be changed by this user")
            self.destinations.delete(actor, destination_id)
            return APIResponse(204)
        return self._method_not_allowed("GET, PATCH, DELETE")

    def _route_resource(self, method, payload, actor, route_id):
        if method == "GET":
            if self.yaml_resource_authority:
                item = next(
                    (
                        value
                        for value in self.configuration_sync.list_routes(actor)
                        if value.id == route_id
                    ),
                    None,
                )
                if item is None:
                    raise KeyError("route not found")
                return APIResponse(200, {"route": {**self._route(item), "management": "yaml"}})
            return APIResponse(200, {"route": self._route(self.routes.get(actor, route_id))})
        if method == "PATCH":
            data = self._object(
                payload,
                {"name", "source", "input_type", "destination_id", "filters", "priority", "enabled"},
            )
            if any(value is None for value in data.values()):
                raise ValueError("route fields cannot be null")
            if self.yaml_resource_authority:
                route = self.configuration_sync.update_route(actor, route_id, data)
                return APIResponse(200, {"route": {**self._route(route), "management": "yaml"}})
            route = self.routes.update(actor, route_id, **data)
            return APIResponse(200, {"route": self._route(route)})
        if method == "DELETE":
            if self.yaml_resource_authority:
                self.configuration_sync.delete_route(actor, route_id)
                return APIResponse(204)
            self.routes.delete(actor, route_id)
            return APIResponse(204)
        return self._method_not_allowed("GET, PATCH, DELETE")

    def _submit_event(self, payload, headers, client) -> APIResponse:
        try:
            notification = self._notification(payload)
            notification.metadata = dict(notification.metadata or {})
            notification.metadata.setdefault("_input_type", "HTTP")
        except (TypeError, ValueError):
            return APIResponse(400, {"error": "request is invalid"})
        token_value = self._bearer(headers)
        token_principal = self.tokens.authenticate(token_value, notification.source)
        actor = token_principal.actor if token_principal else None
        if token_principal is not None:
            if not self.token_limiter.allow(token_principal, str(client)):
                return APIResponse(429, {"error": "rate limit exceeded"})
        else:
            session = self._session(headers, require_csrf=True, touch=True)
            actor = session.actor if session else None
            if session is not None:
                session_rate = Principal(
                    name=f"platform-session:{session.session_id}",
                    role=session.role,
                    sources=frozenset(),
                    rate_limit_per_minute=240,
                )
                if not self.session_limiter.allow(session_rate, str(client)):
                    return APIResponse(429, {"error": "rate limit exceeded"})
        if actor is None:
            return APIResponse(401, {"error": "authentication required"})
        try:
            summary = self.delivery.deliver(actor, notification)
            self.audit.write(
                actor,
                "event.submit",
                "event",
                None,
                "success",
                {"source": notification.source, "matched": summary.matched_routes},
            )
        except Exception as error:
            return self._unexpected("/api/v2/events", error)
        return APIResponse(
            202,
            {
                "accepted": True,
                "matched": summary.matched_routes,
                "delivered": summary.delivered,
                "failed": summary.failed,
                "attempts": summary.attempts,
            },
        )

    def _session(self, headers, *, require_csrf, touch=False):
        token = self._session_token(headers)
        csrf = self._header(headers, "X-CSRF-Token")
        return self.sessions.authenticate(
            token,
            csrf_token=csrf,
            require_csrf=require_csrf,
            touch=touch,
        )

    def _session_token(self, headers) -> str:
        raw = self._header(headers, "Cookie")
        if not raw:
            return ""
        try:
            parsed = SimpleCookie()
            parsed.load(raw)
        except Exception:
            return ""
        names = (
            ("__Host-nowlert_session", "nowlert_session")
            if self.secure_cookies
            else ("nowlert_session", "__Host-nowlert_session")
        )
        for name in names:
            if name in parsed:
                return str(parsed[name].value)
        return ""

    @staticmethod
    def _header(headers, name) -> str:
        if hasattr(headers, "get"):
            direct = headers.get(name)
            if direct is not None:
                return str(direct)
        wanted = str(name).casefold()
        for key, value in (headers or {}).items():
            if str(key).casefold() == wanted:
                return str(value)
        return ""

    def _bearer(self, headers) -> str:
        authorization = self._header(headers, "Authorization")
        if authorization.casefold().startswith("bearer "):
            return authorization[7:].strip()
        return self._header(headers, "X-Nowlert-Token")

    def _notification(self, value):
        if not isinstance(value, dict):
            raise ValueError("event is required")
        parsed = self.dispatcher.parse_webhook("event_api", value)
        if parsed is None:
            raise ValueError("event is invalid")
        return parsed

    def _clear_cookies(self):
        session_name = (
            "__Host-nowlert_session" if self.secure_cookies else "nowlert_session"
        )
        csrf_name = "__Host-nowlert_csrf" if self.secure_cookies else "nowlert_csrf"
        secure = "; Secure" if self.secure_cookies else ""
        return (
            (
                "Set-Cookie",
                f"{session_name}=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0{secure}",
            ),
            (
                "Set-Cookie",
                f"{csrf_name}=; Path=/; SameSite=Strict; Max-Age=0{secure}",
            ),
            ("Cache-Control", "no-store"),
        )

    @staticmethod
    def _object(value, allowed):
        if not isinstance(value, dict) or set(value) - set(allowed):
            raise ValueError("request contains unsupported fields")
        return dict(value)

    @staticmethod
    def _boolean(data, key, default=None):
        if key not in data:
            return default
        value = data[key]
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean")
        return value

    @staticmethod
    def _owner(data, actor):
        owner_id = str(data.get("owner_user_id") or actor.user_id)
        if owner_id != actor.user_id and not actor.is_admin:
            raise PermissionError("owner cannot be changed")
        if not _RESOURCE_ID.fullmatch(owner_id):
            raise ValueError("owner_user_id is invalid")
        return owner_id

    @staticmethod
    def _require_admin(actor):
        if not actor.is_admin:
            raise PermissionError("administrator access is required")

    @staticmethod
    def _email_password_configured(value):
        if isinstance(value, dict):
            candidate = value.get("password")
            if candidate is None:
                candidate = value.get("value")
            return bool(str(candidate or "").strip())
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return False
            if text.startswith("{"):
                try:
                    decoded = json.loads(text)
                except json.JSONDecodeError:
                    return bool(text)
                if isinstance(decoded, dict):
                    candidate = decoded.get("password")
                    if candidate is None:
                        candidate = decoded.get("value")
                    return bool(str(candidate or "").strip())
            return bool(text)
        return False

    @staticmethod
    def _secret_value(value):
        if isinstance(value, str):
            text = value
        elif isinstance(value, dict):
            text = json.dumps(value, sort_keys=True, separators=(",", ":"))
        else:
            raise ValueError("secret must be a string or object")
        if not text or len(text.encode("utf-8")) > 64 * 1024:
            raise ValueError("secret is empty or too large")
        return text

    @staticmethod
    def _secret_name(destination_name):
        return f"{str(destination_name or 'destination')[:80]} {uuid.uuid4().hex[:12]}"

    @staticmethod
    def _method_not_allowed(allow):
        return APIResponse(405, None, (("Allow", allow),))

    @staticmethod
    def _user(item):
        return {
            "id": item.id,
            "username": item.username,
            "role": item.role,
            "enabled": item.enabled,
            "locked_until": item.locked_until,
            "last_login_at": item.last_login_at,
            "first_login_at": item.first_login_at,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "avatar_data": item.avatar_data,
            "mfa_enabled": item.mfa_enabled,
        }

    @staticmethod
    def _token(item):
        return {
            "id": item.id,
            "owner_user_id": item.owner_user_id,
            "name": item.name,
            "role": item.role,
            "source_scopes": list(item.source_scopes),
            "rate_limit_per_minute": item.rate_limit_per_minute,
            "version": item.version,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "expires_at": item.expires_at,
            "last_used_at": item.last_used_at,
            "revoked_at": item.revoked_at,
            "enabled": item.enabled,
        }

    @staticmethod
    def _email_group(item):
        return {
            "id": item.id,
            "owner_user_id": item.owner_user_id,
            "name": item.name,
            "description": item.description,
            "enabled": item.enabled,
            "quiet_window_seconds": item.quiet_window_seconds,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    @staticmethod
    def _email_rule(item):
        return {
            "id": item.id,
            "owner_user_id": item.owner_user_id,
            "group_id": item.group_id,
            "name": item.name,
            "classification": item.classification,
            "match_mode": item.match_mode,
            "conditions": [dict(value) for value in item.conditions],
            "priority": item.priority,
            "enabled": item.enabled,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    @staticmethod
    def _email_message(item):
        return {
            "id": item.id,
            "owner_user_id": item.owner_user_id,
            "mailbox_id": item.mailbox_id,
            "sender": item.sender,
            "sender_domain": item.sender_domain,
            "recipients": list(item.recipients),
            "subject": item.subject,
            "folder": item.folder,
            "labels": list(item.labels),
            "provider_deep_link": item.provider_deep_link,
            "received_at": item.received_at,
        }

    @staticmethod
    def _email_processing(item):
        return {
            "id": item.id,
            "message_id": item.message_id,
            "group_id": item.group_id,
            "rule_id": item.rule_id,
            "action": item.action,
            "classification": item.classification,
            "details": item.details,
            "event_id": item.event_id,
            "created_at": item.created_at,
        }

    @staticmethod
    def _email_mailbox(item):
        return {
            "id": item.id,
            "owner_user_id": item.owner_user_id,
            "provider": item.provider,
            "name": item.name,
            "address": item.address,
            "settings": item.settings,
            "enabled": item.enabled,
            "secret_configured": item.secret_configured,
            "connection_state": item.connection_state,
            "last_sync_at": item.last_sync_at,
            "last_error_code": item.last_error_code,
            "last_error_safe": item.last_error_safe,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    @staticmethod
    def _destination(item):
        return {
            "id": item.id,
            "owner_user_id": item.owner_user_id,
            "name": item.name,
            "output_type": item.output_type,
            "settings": item.settings,
            "shared": item.shared,
            "enabled": item.enabled,
            "secret_configured": item.secret_configured,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
            "last_test_at": item.last_test_at,
            "last_test_outcome": item.last_test_outcome,
            "last_test_response_status": item.last_test_response_status,
            "last_test_error_code": item.last_test_error_code,
            "last_test_safe_error": item.last_test_safe_error,
        }

    @staticmethod
    def _route(item):
        return {
            "id": item.id,
            "owner_user_id": item.owner_user_id,
            "destination_id": item.destination_id,
            "name": item.name,
            "source": item.source,
            "input_type": item.input_type,
            "filters": {key: list(values) for key, values in item.filters.items()},
            "priority": item.priority,
            "priority_name": route_priority_name(item.priority),
            "enabled": item.enabled,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    @staticmethod
    def _delivery(item):
        return {
            "id": item.id,
            "delivery_id": item.delivery_id,
            "owner_user_id": item.owner_user_id,
            "route_id": item.route_id,
            "destination_id": item.destination_id,
            "source": item.source,
            "title": item.title,
            "severity": item.severity,
            "outcome": item.outcome,
            "attempt_number": item.attempt_number,
            "retryable": item.retryable,
            "response_status": item.response_status,
            "error_code": item.error_code,
            "safe_error": item.safe_error,
            "created_at": item.created_at,
            "completed_at": item.completed_at,
            "input_type": item.input_type,
            "device_name": item.device_name,
            "event_name": item.event_name,
            "event_description": item.event_description,
            "event_status": item.event_status,
        }

    @staticmethod
    def _delivery_result(item):
        return {
            "success": item.success,
            "retryable": item.retryable,
            "response_status": item.response_status,
            "error_code": item.error_code,
            "safe_error": sanitize_text(item.safe_error)[:500],
        }

    def _audit_items(self, events):
        usernames = {user.id: user.username for user in self.users.list()}
        return [self._audit(item, usernames) for item in events]

    @staticmethod
    def _audit(item, usernames=None):
        actor_username = None
        if item.actor_user_id:
            actor_username = (usernames or {}).get(item.actor_user_id)

        return {
            "id": item.id,
            "actor_user_id": item.actor_user_id,
            "actor_username": actor_username,
            "action": item.action,
            "resource_type": item.resource_type,
            "resource_id": item.resource_id,
            "outcome": item.outcome,
            "details": item.details,
            "created_at": item.created_at,
        }

    def _unexpected(self, path: str, error: Exception) -> APIResponse:
        reference = uuid.uuid4().hex[:12]
        log.exception(
            "Platform API request failed reference=%s path=%s",
            reference,
            path,
        )
        return APIResponse(
            500,
            {
                "error": "Nowlert could not complete this request.",
                "code": "internal_error",
                "reference": reference,
                "path": path,
            },
        )

    @staticmethod
    def _terminate_process():
        os.kill(os.getpid(), signal.SIGTERM)

    @staticmethod
    def _version_key(value):
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value or "").strip())
        return tuple(int(part) for part in match.groups()) if match else (0, 0, 0)