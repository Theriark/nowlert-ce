"""Round-48 regression for pulsing Routing Flow border sockets."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_routing_flow_uses_pulsing_border_sockets_on_connected_sides():
    script = read("src/webui/routing_flow.js")
    css = read("src/webui/routing_flow.css")

    create_start = script.index("function createNode(kind, identity, label)")
    create_end = script.index("function renderMetrics()", create_start)
    create = script[create_start:create_end]

    assert 'rf-socket rf-socket-left' in create
    assert 'rf-socket rf-socket-right' in create
    assert 'leftSocket.setAttribute("aria-hidden", "true")' in create
    assert 'rightSocket.setAttribute("aria-hidden", "true")' in create

    draw_start = script.index("function drawEdges()")
    draw_end = script.index("function stopPulses()", draw_start)
    draw = script[draw_start:draw_end]

    assert '".rf-node.rf-has-incoming, .rf-node.rf-has-outgoing"' in draw
    assert 'classList.remove("rf-has-incoming")' in draw
    assert 'classList.remove("rf-has-outgoing")' in draw
    assert 'route.classList.add("rf-has-outgoing")' in draw
    assert 'a.classList.add("rf-has-outgoing")' in draw
    assert 'b.classList.add("rf-has-incoming")' in draw

    assert ".rf-node.rf-has-incoming::after" not in css
    assert ".rf-socket {" in css
    assert "height:20px;" in css
    assert "width:2px;" in css
    assert ".rf-node.rf-has-incoming > .rf-socket-left" in css
    assert ".rf-node.rf-has-outgoing > .rf-socket-right" in css
    assert "animation:rf-socket-pulse 2.2s ease-in-out infinite;" in css
    assert "@keyframes rf-socket-pulse" in css
    assert "box-shadow:0 0 5px rgba(255,209,58,.95),0 0 14px rgba(255,185,22,.48);" in css

    reduced_start = css.rindex("@media (prefers-reduced-motion: reduce)")
    reduced = css[reduced_start:]
    assert ".rf-socket-left" in reduced
    assert ".rf-socket-right" in reduced
    assert "animation:none;" in reduced
