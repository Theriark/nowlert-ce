"""Every script and stylesheet link carries its content hash, so a proxy that
replaces "no-cache" with a long browser TTL (Cloudflare did, max-age=14400)
can never pair a new page with an old script or stylesheet."""

import hashlib
import re
import shutil
from pathlib import Path

from webui.service import UI_BUILD, WebUIService

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r'(?:href|src)="(/ui/[^"]+\.(?:css|js))(\?[^"]*)?"')


class Configuration:
    def get(self, section, key, default=None):
        return default


def _links(service):
    page = service.response("/").body.decode("utf-8")
    return page, LINK.findall(page)


def test_every_script_and_stylesheet_link_carries_its_content_hash():
    service = WebUIService(Configuration(), root=ROOT)
    page, links = _links(service)
    assert len(links) >= 20
    for route, query in links:
        relative = service.assets[route][0]
        expected = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()[:12]
        assert query.endswith(f"h={expected}"), (route, query)
    # Existing build versions stay in place; the hash is added after them.
    assert f"/ui/app.js?v={UI_BUILD}&h=" in page
    assert '/ui/styles.css?h=' in page
    assert '/ui/enhancements.js?h=' in page
    # The fingerprinted URL still resolves to the same file.
    assert service.response("/ui/styles.css").status == 200


def test_a_changed_file_gets_a_new_url(tmp_path):
    shutil.copytree(ROOT / "src", tmp_path / "src")
    before = dict(_links(WebUIService(Configuration(), root=tmp_path))[1])
    styles = tmp_path / "src" / "webui" / "styles.css"
    styles.write_text(styles.read_text(encoding="utf-8") + "\n/* changed */\n", encoding="utf-8")
    after = dict(_links(WebUIService(Configuration(), root=tmp_path))[1])
    assert after["/ui/styles.css"] != before["/ui/styles.css"]
    assert after["/ui/app.js"] == before["/ui/app.js"]
