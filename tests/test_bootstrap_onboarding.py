from __future__ import annotations

from pathlib import Path

from webui.service import WebUIService


ROOT = Path(__file__).resolve().parents[1]


class Configuration:
    def get(self, *keys, default=None):
        return default


def test_first_run_setup_serves_the_guided_layout_and_responsive_styles():
    service = WebUIService(Configuration(), root=ROOT)
    page = service.response("/")
    assert page is not None and page.status == 200
    markup = page.body.decode("utf-8")

    assert 'id="bootstrap-view" class="login-view bootstrap-onboarding"' in markup
    assert '<aside class="bootstrap-intro" aria-labelledby="bootstrap-title">' in markup
    assert 'aria-current="step"' in markup
    assert "Connect integrations" in markup
    assert "Create routes" in markup
    assert 'id="bootstrap-form"' in markup
    assert 'id="bootstrap-password-help"' in markup
    assert 'href="/ui/bootstrap_onboarding.css?v=20260929-bootstrap-onboarding-1"' in markup

    stylesheet = service.response("/ui/bootstrap_onboarding.css")
    assert stylesheet is not None and stylesheet.status == 200
    assert stylesheet.content_type.startswith("text/css")
    assert b"#bootstrap-view.bootstrap-onboarding" in stylesheet.body
    assert b"@media (max-width: 760px)" in stylesheet.body
