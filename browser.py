#!/usr/bin/env python3

from dataclasses import dataclass
import gzip
from io import BytesIO
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM, socket
from typing import Dict, TextIO, Tuple

DEFAULT_HTTP_PORT = 80
HTTP_PROTOCOL_PREFIX = "http://"
URL_PATH_SEP = "/"
CRLF = "\r\n"
ENCODING = "utf8"
GZIP_ENCODING = "gzip"
HEADER_CONTENT_ENCODING = "content-encoding"
HEADER_ACCEPT_ENCODING = "accept-encoding"


@dataclass
class URL:
    raw: str
    host: str
    path: str

    @staticmethod
    def parse(url: str) -> "URL":
        raw = url
        assert url.startswith(HTTP_PROTOCOL_PREFIX)
        url = url[len(HTTP_PROTOCOL_PREFIX) :]

        if URL_PATH_SEP not in url:
            url += URL_PATH_SEP

        host, path = url.split(URL_PATH_SEP, maxsplit=1)
        path = URL_PATH_SEP + path

        return URL(raw=raw, host=host, path=path)


def request(url: str) -> Tuple[Dict[str, str], str]:
    parsed = URL.parse(url)
    s = socket(family=AF_INET, type=SOCK_STREAM, proto=IPPROTO_TCP)
    s.connect((parsed.host, 80))
    s.send(
        f"GET {parsed.path} HTTP/1.0{CRLF}Host: {parsed.host}{CRLF}{HEADER_ACCEPT_ENCODING}: {GZIP_ENCODING}{CRLF}{CRLF}".encode(
            ENCODING
        )
    )
    response: BytesIO = s.makefile("rb", encoding=ENCODING, newline=CRLF)
    statusline = response.readline().decode(ENCODING)
    version, status, explanation = statusline.split(" ", 2)
    assert status == "200", "{}: {}".format(status, explanation)

    headers = {}
    while True:
        line = response.readline().decode(ENCODING)
        if line == CRLF:
            break
        header, value = line.split(":", 1)
        headers[header.lower()] = value.strip()

    encoding = headers.get(HEADER_CONTENT_ENCODING, "")
    if encoding.lower() == GZIP_ENCODING:
        body = gzip.decompress(response.read()).decode(ENCODING)
    else:
        body = response.read().decode(ENCODING)

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
