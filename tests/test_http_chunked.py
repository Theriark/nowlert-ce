"""Real socket regression coverage for controller HTTP request framing."""

import http.client
import json
import socket
import threading
from pathlib import Path

import pytest

from dispatcher import Dispatcher
from inputs.http import HTTPServer
from inputs.http import HTTPHandler
from inputs.http_body import BodyError


class Router:
    def __init__(self):
        self.notifications = []

    def route(self, notification):
        self.notifications.append(notification)


@pytest.fixture
def receiver():
    router = Router()
    server = HTTPServer(("127.0.0.1", 0), Dispatcher(), router, 4096, "test-secret")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, router
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def raw_post(receiver, body, headers="Transfer-Encoding: chunked\r\n", token="test-secret", path="/redfish/hpe"):
    server, _ = receiver
    with socket.create_connection(server.server_address, timeout=2) as connection:
        connection.sendall(
            f"POST {path} HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
            f"X-Nowlert-Token: {token}\r\n{headers}\r\n".encode() + body
        )
        connection.shutdown(socket.SHUT_WR)
        response = http.client.HTTPResponse(connection)
        response.begin()
        response.read()
        return response.status


@pytest.mark.parametrize(("vendor", "fixture", "source"), [
    ("hpe", "hpe_memory.json", "hpe_ilo"),
    ("dell", "dell_storage.json", "dell_idrac"),
    ("supermicro", "supermicro_thermal.json", "supermicro"),
])
def test_controller_chunked_envelope_routes_and_deduplicates(receiver, vendor, fixture, source):
    value = json.loads((Path(__file__).parent / "fixtures" / "redfish" / fixture).read_text())
    body = json.dumps(value, ensure_ascii=False).encode()
    chunks = [body[:19], body[19:53], body[53:]]
    framed = b"".join(f"{len(chunk):X};controller=test\r\n".encode() + chunk + b"\r\n" for chunk in chunks)
    framed += b"0\r\nX-Test-Trailer: complete\r\n\r\n"
    assert raw_post(receiver, framed, path=f"/redfish/{vendor}") == 204
    assert raw_post(receiver, framed, path=f"/redfish/{vendor}") == 204
    notifications = receiver[1].notifications
    assert len(notifications) == 1
    assert notifications[0].source == source
    assert notifications[0].metadata["_input_type"] == "Redfish"


@pytest.mark.parametrize(("body", "headers", "status"), [
    (b"1001\r\n", "Transfer-Encoding: chunked\r\n", 413),
    (b"900\r\n" + b"x" * 2304 + b"\r\n900\r\n", "Transfer-Encoding: chunked\r\n", 413),
    (b"garbage\r\n", "Transfer-Encoding: chunked\r\n", 400),
    (b"+2\r\n{}\r\n0\r\n\r\n", "Transfer-Encoding: chunked\r\n", 400),
    (b"2\n{}\n0\n\n", "Transfer-Encoding: chunked\r\n", 400),
    (b"2\r\n{", "Transfer-Encoding: chunked\r\n", 400),
    (b"2\r\n{}xx0\r\n\r\n", "Transfer-Encoding: chunked\r\n", 400),
    (b"0\r\ninvalid trailer\r\n\r\n", "Transfer-Encoding: chunked\r\n", 400),
    (b"0\r\n" + b"X: " + b"x" * 8192 + b"\r\n\r\n", "Transfer-Encoding: chunked\r\n", 400),
    (b"1;" + b"x" * 8192 + b"\r\nx\r\n0\r\n\r\n", "Transfer-Encoding: chunked\r\n", 400),
    (b"2\r\n{}\r\n0\r\n\r\n", "Transfer-Encoding: gzip, chunked\r\n", 400),
    (b"2\r\n{}\r\n0\r\n\r\n", "Transfer-Encoding: chunked\r\nContent-Length: 2\r\n", 400),
    (b"0\r\n\r\n", "Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked\r\n", 400),
    (b"{}", "Content-Length: 2\r\nContent-Length: 2\r\n", 400),
    (b"{}", "Content-Length: 3\r\n", 400),
    (b"{}", "Content-Length: -1\r\n", 400),
])
def test_rejects_invalid_or_oversized_body_without_routing(receiver, body, headers, status):
    assert raw_post(receiver, body, headers) == status
    assert receiver[1].notifications == []


def test_chunked_request_still_requires_token(receiver):
    assert raw_post(receiver, b"2\r\n{}\r\n0\r\n\r\n", token="wrong") == 401
    assert receiver[1].notifications == []


def test_rejects_excessive_chunk_framing(receiver):
    framed = (b"1;" + b"x" * 4090 + b"\r\nx\r\n") * 17 + b"0\r\n\r\n"
    assert raw_post(receiver, framed) == 400
    assert receiver[1].notifications == []


def test_chunked_api_body_reaches_api_without_buffering_proxy(receiver):
    server, _ = receiver
    observed = []
    original = server.api.handle_http

    def recording(method, path, payload, headers, address):
        observed.append(payload)
        return original(method, path, payload, headers, address)

    server.api.handle_http = recording
    raw_post(receiver, b"2\r\n{}\r\n0\r\n\r\n", path="/api/nonexistent")
    assert observed == [{}]


def test_body_timeout_returns_408_and_restores_socket_timeout():
    class Connection:
        timeout = None

        def gettimeout(self):
            return self.timeout

        def settimeout(self, timeout):
            self.timeout = timeout

    class Stream:
        def read(self, _size):
            raise TimeoutError()

    from email.message import Message

    handler = HTTPHandler.__new__(HTTPHandler)
    handler.connection = Connection()
    handler.headers = Message()
    handler.headers["Content-Length"] = "10"
    handler.rfile = Stream()
    handler.server = type("Server", (), {"max_body_bytes": 4096})()
    with pytest.raises(BodyError) as error:
        handler._read_body()
    assert error.value.status == 408
    assert handler.connection.timeout is None
