"""Bounded HTTP request framing for native webhook and API inputs."""

from __future__ import annotations

import re


class BodyError(ValueError):
    def __init__(self, status: int = 400):
        super().__init__("invalid HTTP request body")
        self.status = status


def read_body(stream, headers, max_bytes: int) -> bytes:
    """Decode one body without accepting ambiguous or unbounded framing."""
    transfers = headers.get_all("Transfer-Encoding", [])
    lengths = headers.get_all("Content-Length", [])
    if transfers:
        # Conflicting framing must never depend on proxy interpretation.
        if lengths or len(transfers) != 1 or transfers[0].strip().lower() != "chunked":
            raise BodyError()
        return _read_chunked(stream, max_bytes)
    if len(lengths) != 1 or not re.fullmatch(r"[0-9]+", lengths[0].strip()):
        raise BodyError()
    try:
        length = int(lengths[0].strip())
    except ValueError:
        raise BodyError() from None
    if length > max_bytes:
        raise BodyError(413)
    return _read_exact(stream, length)


def _read_exact(stream, length: int) -> bytes:
    body = stream.read(length)
    if len(body) != length:
        raise BodyError()
    return body


def _read_chunked(stream, max_bytes: int) -> bytes:
    body = bytearray()
    framing_bytes = 0
    while True:
        line = stream.readline(8193)
        framing_bytes += len(line)
        if len(line) > 8192 or framing_bytes > 65536 or not line.endswith(b"\r\n"):
            raise BodyError()
        size_text, _, extensions = line[:-2].partition(b";")
        if not re.fullmatch(rb"[0-9a-fA-F]+", size_text):
            raise BodyError()
        if any(byte < 32 or byte == 127 for byte in extensions):
            raise BodyError()
        size = int(size_text, 16)
        if size > max_bytes - len(body):
            raise BodyError(413)
        if not size:
            # Consume trailers, but never use them as authentication/framing.
            while True:
                line = stream.readline(8193)
                framing_bytes += len(line)
                if len(line) > 8192 or framing_bytes > 65536 or not line.endswith(b"\r\n"):
                    raise BodyError()
                if line == b"\r\n":
                    return bytes(body)
                name, separator, value = line[:-2].partition(b":")
                if not separator or not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
                    raise BodyError()
                if any(byte < 32 and byte != 9 or byte == 127 for byte in value):
                    raise BodyError()
        body.extend(_read_exact(stream, size))
        if _read_exact(stream, 2) != b"\r\n":
            raise BodyError()
        framing_bytes += 2
