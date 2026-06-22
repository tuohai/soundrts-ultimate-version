import socket

from .lib.log import warning

BROADCAST_PORT = 2500  # not necessarily options.port
CALL = b"SoundRTS_client"
RESPONSE_PREFIX = b"SoundRTS_server: "


def server_loop(info):
    response = RESPONSE_PREFIX + info.encode(errors="ignore")
    s = socket.socket(type=socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("", BROADCAST_PORT))
    except OSError as exc:
        warning(
            "couldn't bind LAN discovery on UDP port %s (%s); "
            "the game server still works via localhost or direct IP",
            BROADCAST_PORT,
            exc,
        )
        return
    while True:
        data, address = s.recvfrom(4096)
        if data == CALL:
            s.sendto(response, address)


def local_server():
    s = socket.socket(type=socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(0.5)
    s.sendto(CALL, ("255.255.255.255", BROADCAST_PORT))
    try:
        data, address = s.recvfrom(4096)
    except OSError:  # timeout
        return
    if data.startswith(RESPONSE_PREFIX):
        return address[0], data[len(RESPONSE_PREFIX) :].decode(errors="ignore")
