from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_round26_import_preview_is_driven_by_backend_preview_payload():
    app = read("src/webui/app.js")
    portability = read("src/storage/portability.py")

    assert "function renderImportPreview(preview)" in app
    assert "function renderImportIssues(preview)" in app
    assert "renderImportPreview(response.preview);" in app
    assert 'const errors = Array.isArray(preview?.errors) ? preview.errors.length : 0;' in app
    assert 'const warnings = Array.isArray(preview?.warnings) ? preview.warnings.length : 0;' in app
    assert 'importPreviewCount(preview, "destinations")' in app
    assert 'importPreviewCount(preview, "routes")' in app
    assert 'JSON.stringify(preview || {}, null, 2)' in app

    preview_block = app[
        app.index("function renderImportPreview(preview)"):
        app.index("async function copyImportPreview()")
    ]
    assert 'textContent = "25"' not in preview_block
    assert 'textContent = "0"' not in preview_block

    assert '"warnings": list(self.warnings)' in portability
    assert '"errors": list(self.errors)' in portability
    assert '"destinations": len(self.destinations)' in portability
    assert '"routes": len(self.routes)' in portability
    assert '"filters": sum(len(item.get("filters") or ()) for item in self.destinations)' in portability


def test_round26_mfa_delete_transport_accepts_json_body():
    transport = read("src/inputs/http.py")
    app = read("src/webui/app.js")
    platform = read("src/api/platform.py")

    assert 'method == "DELETE"' in transport
    assert "delete_has_body" in transport
    assert 'method in {"POST", "PUT", "PATCH"} or delete_has_body' in transport
    assert 'method: "DELETE"' in app
    assert 'body: {' in app[app.index("async function disableMfa"):app.index("async function copyMfaSecret")]
    assert 'data = self._object(payload, {"password", "code"})' in platform
