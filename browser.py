#!/usr/bin/env python3

from dataclasses import dataclass
import gzip
from io import BytesIO
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM, socket
from typing import Dict, Tuple
import ssl

DEFAULT_HTTP_PORT = 80
HTTP_PROTOCOL_PREFIX = "http://"
URL_PATH_SEP = "/"

NEWLINE = "\r\n"

ENCODING_UTF8 = "utf8"
ENCODING_GZIP = "gzip"

HEADER_CONTENT_ENCODING = "content-encoding"
HEADER_ACCEPT_ENCODING = "accept-encoding"


@dataclass
class URL:
    raw: str
    host: str
    path: str
    scheme: str
    port: int

    @staticmethod
    def parse(url: str) -> "URL":
        raw = url
        scheme, url = url.split("://", 1)
        assert scheme in ["http", "https"]
        port = 80 if scheme == "http" else 443

        if URL_PATH_SEP not in url:
            url += URL_PATH_SEP

        host, path = url.split(URL_PATH_SEP, maxsplit=1)
        path = URL_PATH_SEP + path

        return URL(raw=raw, host=host, path=path, port=port, scheme=scheme)


def request(url: str) -> Tuple[Dict[str, str], str]:
    parsed = URL.parse(url)
    s = socket(family=AF_INET, type=SOCK_STREAM, proto=IPPROTO_TCP)

    if parsed.scheme == "https":
        ctx = ssl.create_default_context()
        s = ctx.wrap_socket(s, server_hostname=parsed.host)

    s.connect((parsed.host, parsed.port))
    s.send(
        f"GET {parsed.path} HTTP/1.0{NEWLINE}Host: {parsed.host}{NEWLINE}{HEADER_ACCEPT_ENCODING}: {ENCODING_GZIP}{NEWLINE}{NEWLINE}".encode(
            ENCODING_UTF8
        )
    )
    response: BytesIO = s.makefile("rb", encoding=ENCODING_UTF8, newline=NEWLINE)
    statusline = response.readline().decode(ENCODING_UTF8)
    version, status, explanation = statusline.split(" ", 2)
    assert status == "200", "{}: {}".format(status, explanation)

    headers = {}
    while True:
        line = response.readline().decode(ENCODING_UTF8)
        if line == NEWLINE:
            break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()

    encoding = headers.get(HEADER_CONTENT_ENCODING, "")
    if encoding.lower() == ENCODING_GZIP:
        body = gzip.decompress(response.read()).decode(ENCODING_UTF8)
    else:
        body = response.read().decode(ENCODING_UTF8)

    s.close()

    return headers, body


def show(body: str):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")


def load(url: str):
    headers, body = request(url)
    show(body=body)


if __name__ == "__main__":
    import sys

    load(sys.argv[1])
