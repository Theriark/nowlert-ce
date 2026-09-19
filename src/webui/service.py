"""Serve a bounded set of packaged WebUI assets with strict browser policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


UI_BUILD = "20260919-r36"


SECURITY_HEADERS = (
    (
        "Content-Security-Policy",
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; connect-src 'self' https://api.github.com; base-uri 'none'; "
        "form-action 'self'; frame-ancestors 'none'",
    ),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
)


@dataclass(frozen=True)
class WebUIResponse:
    status: int
    body: bytes = b""
    content_type: str = ""
    cache_control: str = "no-store"


class WebUIService:
    """Resolve only known packaged assets; never map request paths to disk."""

    def __init__(
        self,
        configuration,
        *,
        root: str | Path | None = None,
        platform_available: bool = True,
    ):
        self.configuration = configuration
        self.platform_available = bool(platform_available)
        self.root = (
            Path(root).resolve()
            if root is not None
            else Path(__file__).resolve().parents[2]
        )
        self.assets = {
            "/": ("src/webui/index.html", "text/html; charset=utf-8", "no-store"),
            "/ui": ("src/webui/index.html", "text/html; charset=utf-8", "no-store"),
            "/ui/": ("src/webui/index.html", "text/html; charset=utf-8", "no-store"),
            "/ui/app.js": (
                "src/webui/app.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/enhancements.js": (
                "src/webui/enhancements.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/qa_patch.js": (
                "src/webui/qa_patch.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/i18n.js": (
                "src/webui/i18n.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/styles.css": (
                "src/webui/styles.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/enhancements.css": (
                "src/webui/enhancements.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/qa_patch.css": (
                "src/webui/qa_patch.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/professional.css": (
                "src/webui/professional.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/dashboard.js": (
                "src/webui/dashboard.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/destination_routes.css": (
                "src/webui/destination_routes.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/destination_routes.js": (
                "src/webui/destination_routes.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/destination_editor_fix.css": (
                "src/webui/destination_editor_fix.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/destination_editor_fix.js": (
                "src/webui/destination_editor_fix.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/filtering.js": (
                "src/webui/filtering.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/filtering.css": (
                "src/webui/filtering.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/source_ui_retirement.js": (
                "src/webui/source_ui_retirement.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/policy_simplification.js": (
                "src/webui/policy_simplification.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/policy_simplification.css": (
                "src/webui/policy_simplification.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/acceptance_cleanup.js": (
                "src/webui/acceptance_cleanup.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/routing_flow.js": (
                "src/webui/routing_flow.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/routing_flow.css": (
                "src/webui/routing_flow.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/filtering_ownership_sync.js": (
                "src/webui/filtering_ownership_sync.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/filtering_ownership_sync.css": (
                "src/webui/filtering_ownership_sync.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/operations_dashboard.js": (
                "src/webui/operations_dashboard.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/operations_dashboard.css": (
                "src/webui/operations_dashboard.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/operations_acceptance.js": (
                "src/webui/operations_acceptance.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/operations_acceptance.css": (
                "src/webui/operations_acceptance.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/page_headers.js": (
                "src/webui/page_headers.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/page_headers.css": (
                "src/webui/page_headers.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/destination_overview_acceptance.js": (
                "src/webui/destination_overview_acceptance.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/destination_overview_acceptance.css": (
                "src/webui/destination_overview_acceptance.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/audit_log_refinement.js": (
                "src/webui/audit_log_refinement.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/audit_log_refinement.css": (
                "src/webui/audit_log_refinement.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/management_consistency.js": (
                "src/webui/management_consistency.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/management_consistency.css": (
                "src/webui/management_consistency.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/reference_acceptance.js": (
                "src/webui/reference_acceptance.js",
                "text/javascript; charset=utf-8",
                "no-cache",
            ),
            "/ui/reference_acceptance.css": (
                "src/webui/reference_acceptance.css",
                "text/css; charset=utf-8",
                "no-cache",
            ),
            "/ui/icon.png": (
                "assets/icons/nowlert.png",
                "image/png",
                "no-cache",
            ),
            "/ui/brand/nowlert-owl-v3.1.0.png": (
                "assets/icons/nowlert.png",
                "image/png",
                "public, max-age=31536000, immutable",
            ),
            "/ui/icons/discord.svg": (
                "assets/icons/discord.svg", "image/svg+xml", "public, max-age=86400"
            ),
            "/ui/icons/mqtt.svg": (
                "assets/icons/mqtt.svg", "image/svg+xml", "public, max-age=86400"
            ),
            "/ui/icons/ntfy.svg": (
                "assets/icons/ntfy.svg", "image/svg+xml", "public, max-age=86400"
            ),
            "/ui/icons/routing-teams.svg": (
                "assets/icons/routing-teams.svg",
                "image/svg+xml",
                "public, max-age=86400",
            ),
            "/ui/icons/routing-slack.svg": (
                "assets/icons/routing-slack.svg",
                "image/svg+xml",
                "public, max-age=86400",
            ),
            "/ui/source-icons/rest-api.svg": (
                "assets/icons/rest-api.svg",
                "image/svg+xml",
                "public, max-age=86400",
            ),
            "/ui/source-icons/redfish.jpg": (
                "assets/icons/redfish.jpg",
                "image/jpeg",
                "public, max-age=86400",
            ),
        }
        for filename in (
            "xen-orchestra.png",
            "grafana.png",
            "portainer.png",
            "proxmox.png",
            "qnap.png",
            "synology.png",
            "truenas.png",
            "unifi-network.png",
            "unifi-protect.png",
            "unifi-drive.png",
            "zabbix.png",
            "supermicro.png",
            "hpe-ilo.png",
            "dell-idrac.png",
            "home-assistant.png",
            "nowlert.png",
        ):
            self.assets[f"/ui/source-icons/{filename}"] = (
                f"assets/icons/{filename}",
                "image/png",
                "public, max-age=86400",
            )

    @property
    def enabled(self) -> bool:
        return self.platform_available and all(
            self.configuration.get(section, "enabled", default=True) is True
            for section in ("http", "api", "platform", "webui")
        )

    def response(self, path: str) -> WebUIResponse | None:
        route = str(path or "")
        if route not in self.assets:
            if route.startswith("/ui/"):
                return WebUIResponse(404)
            return None
        if not self.enabled:
            return WebUIResponse(404)
        relative, content_type, cache_control = self.assets[route]
        asset = self.root / relative
        try:
            body = asset.read_bytes()
        except OSError:
            return WebUIResponse(404)
        if route in {"/", "/ui", "/ui/"}:
            text = body.decode("utf-8")
            version = f"?v={UI_BUILD}"
            extension = (
                f'  <link rel="stylesheet" href="/ui/filtering.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/destination_routes.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/destination_editor_fix.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/policy_simplification.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/routing_flow.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/filtering_ownership_sync.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/operations_dashboard.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/operations_acceptance.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/page_headers.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/destination_overview_acceptance.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/audit_log_refinement.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/management_consistency.css{version}">\n'
                f'  <link rel="stylesheet" href="/ui/reference_acceptance.css{version}">\n'
                f'  <script src="/ui/filtering.js{version}" defer></script>\n'
                f'  <script src="/ui/source_ui_retirement.js{version}" defer></script>\n'
                f'  <script src="/ui/destination_routes.js{version}" defer></script>\n'
                f'  <script src="/ui/destination_editor_fix.js{version}" defer></script>\n'
                f'  <script src="/ui/policy_simplification.js{version}" defer></script>\n'
                f'  <script src="/ui/acceptance_cleanup.js{version}" defer></script>\n'
                f'  <script src="/ui/routing_flow.js{version}" defer></script>\n'
                f'  <script src="/ui/filtering_ownership_sync.js{version}" defer></script>\n'
                f'  <script src="/ui/operations_dashboard.js{version}" defer></script>\n'
                f'  <script src="/ui/operations_acceptance.js{version}" defer></script>\n'
                f'  <script src="/ui/page_headers.js{version}" defer></script>\n'
                f'  <script src="/ui/destination_overview_acceptance.js{version}" defer></script>\n'
                f'  <script src="/ui/audit_log_refinement.js{version}" defer></script>\n'
                f'  <script src="/ui/management_consistency.js{version}" defer></script>\n'
                f'  <script src="/ui/reference_acceptance.js{version}" defer></script>\n'
            )
            body = text.replace("</head>", extension + "</head>", 1).encode("utf-8")
        return WebUIResponse(200, body, content_type, cache_control)

    def redirect_location(self, path: str, headers) -> str | None:
        """Return the configured HTTPS public URL for plain-HTTP UI requests."""

        if self.configuration.get(
            "webui", "enforce_https", default=False
        ) is not True:
            return None
        public_url = str(
            self.configuration.get("webui", "public_url", default="") or ""
        ).strip().rstrip("/")
        if not public_url:
            return None
        parsed = urlsplit(public_url)
        if parsed.scheme.casefold() != "https" or not parsed.netloc:
            return None
        forwarded = str(headers.get("X-Forwarded-Proto", "") or "").casefold()
        if forwarded == "https":
            return None
        suffix = "/" if path in {"", "/"} else path
        return f"{public_url}{suffix}"
