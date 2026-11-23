#!/usr/bin/env python3
"""Minimal HTTP CONNECT proxy that pins github.com to a working IP.

Why this exists
---------------
On this machine the DNS resolver answers ``github.com`` with
``20.205.243.166``, whose TCP connections are reset, while
``api.github.com`` resolves to addresses that work fine.  The default git
SOCKS proxy (``socks5://127.0.0.1:10808``) is often closed as well, so
``git push`` fails with "connection reset by peer".

Rather than editing the system hosts file or the user's global git
config, run this local CONNECT proxy and point git at it for the single
command that needs it::

    python tools/pin_connect_proxy.py 10809 &
    git -c http.sslBackend=schannel -c http.proxy=http://127.0.0.1:10809 push origin main

The proxy relays CONNECT tunnels to the pinned address and falls back
through the remaining candidates if the first one refuses the
connection.  Plain (non-CONNECT) requests are refused.

Options
-------
``PORT``
    TCP port to listen on (default 10809).  Only ``127.0.0.1`` is bound.
``IP [IP ...]``
    Candidate addresses for ``github.com``, tried in order.  The default
    list is below; override it to pin a different address.
"""
from __future__ import annotations

import select
import socket
import sys
import threading

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 10809

# Candidate addresses for github.com, tried in order.  The first one that
# completes the TCP handshake wins.
PIN_IPS = [ip for ip in (sys.argv[2:] or [
    "20.27.177.113",
    "20.205.243.166",
    "20.248.137.48",
]) if ip]

PINNED_HOSTS = ("github.com", "www.github.com")


def pipe(a: socket.socket, b: socket.socket) -> None:
    """Relay bytes in both directions until either side closes."""
    socks = [a, b]
    try:
        while True:
            r, _, x = select.select(socks, [], socks, 60)
            if x:
                break
            if not r:
                continue
            for s in r:
                try:
                    data = s.recv(65536)
                except OSError:
                    return
                if not data:
                    return
                dst = b if s is a else a
                try:
                    dst.sendall(data)
                except OSError:
                    return
    finally:
        for s in socks:
            try:
                s.close()
            except OSError:
                pass


def connect_upstream(host: str, port: int) -> socket.socket:
    """Open a connection to *host*, using the pinned IPs for github.com."""
    if host.lower() in PINNED_HOSTS:
        last_error = None
        for ip in PIN_IPS:
            try:
                return socket.create_connection((ip, port), timeout=20)
            except OSError as exc:
                last_error = exc
                print(f"  pinned {ip} failed: {exc!r}", flush=True)
        raise OSError(f"no pinned address worked for {host}: {last_error!r}")
    return socket.create_connection((host, port), timeout=20)


def handle(client: socket.socket) -> None:
    try:
        client.settimeout(20)
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = client.recv(4096)
            if not chunk:
                print("client closed before CONNECT", flush=True)
                return
            buf += chunk
        line = buf.split(b"\r\n", 1)[0].decode("latin-1")
        print(f"CONNECT request: {line!r}", flush=True)
        if not line.upper().startswith("CONNECT"):
            client.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
            return
        target = line.split()[1]
        host, _, port = target.rpartition(":")
        host = host.strip("[]")
        port = int(port or 443)
        upstream = connect_upstream(host, port)
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        client.settimeout(None)
        upstream.settimeout(None)
        pipe(client, upstream)
    except Exception as exc:
        print(f"handle error: {exc!r}", flush=True)
        try:
            client.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        except OSError:
            pass
        try:
            client.close()
        except OSError:
            pass


def main() -> int:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", PORT))
    srv.listen(64)
    print(f"pin proxy on 127.0.0.1:{PORT} -> {', '.join(PIN_IPS)}", flush=True)
    while True:
        client, _ = srv.accept()
        threading.Thread(target=handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    raise SystemExit(main())
