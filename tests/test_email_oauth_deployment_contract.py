"""Self-hosted Email Alerts OAuth deployment contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_compose_prefers_mounted_oauth_secret_files():
    compose = (ROOT / "compose.production.yaml").read_text(encoding="utf-8")
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "NOWLERT_EMAIL_GMAIL_CLIENT_SECRET_FILE" in compose
    assert "/run/secrets/nowlert_email_gmail_client_secret" in compose
    assert "NOWLERT_EMAIL_MICROSOFT_CLIENT_SECRET_FILE" in compose
    assert "/run/secrets/nowlert_email_microsoft_client_secret" in compose
    assert '"${NOWLERT_SECRETS_DIR:-./secrets}:/run/secrets:ro"' in compose

    assert "NOWLERT_EMAIL_GMAIL_CLIENT_SECRET_FILE=" in example
    assert "NOWLERT_EMAIL_MICROSOFT_CLIENT_SECRET_FILE=" in example
    assert "\nNOWLERT_EMAIL_GMAIL_CLIENT_SECRET=\n" not in example
    assert "\nNOWLERT_EMAIL_MICROSOFT_CLIENT_SECRET=\n" not in example
    assert "secrets/" in gitignore


def test_oauth_documentation_declares_per_installation_secret_ownership():
    deployment = (ROOT / "docs" / "deployment.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "per-installation OAuth model" in deployment
    assert "Theriark does not ship a shared OAuth client secret" in deployment
    assert "Docker Swarm/Portainer" in deployment
    assert "legacy `NOWLERT_EMAIL_*_CLIENT_SECRET` environment variable" in deployment
    assert "does not contain a Theriark-owned OAuth secret" in readme
