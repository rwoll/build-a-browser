#!/usr/bin/env python

from dataclasses import dataclass
import gzip
from io import BytesIO
from socket import AF_INET, IPPROTO_TCP, SOCK_STREAM, socket
from typing import Dict, Tuple
import ssl
import tkinter

DEFAULT_HTTP_PORT = 80
HTTP_PROTOCOL_PREFIX = "http://"
URL_PATH_SEP = "/"

NEWLINE = "\r\n"

ENCODING_UTF8 = "utf8"
ENCODING_GZIP = "gzip"

HEADER_CONTENT_ENCODING = "content-encoding"
HEADER_ACCEPT_ENCODING = "accept-encoding"

WIDTH, HEIGHT = 800, 600


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
        if ":" in host:
            host, port = host.split(":", 1)
            port = int(port)

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


def lex(body: str) -> str:
    text = ""
    in_angle = False
    for c in body:
        if c == "<":
            in_angle = True
        elif c == ">":
            in_angle = False
        elif not in_angle:
            text += c

    return text


def load(url: str):
    headers, body = request(url)
    lex(body=body)


class Browser:
    def __init__(self) -> None:
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
        )
        self.canvas.pack()

    def load(self, url: str):
        headers, body = request(url=url)
        text = lex(body=body)

        HSTEP, VSTEP = 13, 18
        cursor_x, cursor_y = HSTEP, VSTEP
        for c in text:
            self.canvas.create_text(cursor_x, cursor_y, text=c)
            cursor_x += HSTEP
            if cursor_x >= WIDTH - HSTEP:
                cursor_y += VSTEP
                cursor_x = HSTEP


if __name__ == "__main__":
    import sys

    Browser().load(sys.argv[1])
    tkinter.mainloop()
