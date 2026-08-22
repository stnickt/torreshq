import socket
import struct

SERVERDATA_AUTH = 3
SERVERDATA_EXECCOMMAND = 2


def _pack(request_id, pkt_type, body):
    payload = struct.pack("<ii", request_id, pkt_type) + body.encode("utf8") + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("RCON connection closed unexpectedly")
        buf += chunk
    return buf


def _read_packet(sock):
    length = struct.unpack("<i", _recv_exact(sock, 4))[0]
    data = _recv_exact(sock, length)
    request_id, pkt_type = struct.unpack("<ii", data[:8])
    body = data[8:-2].decode("utf8", errors="replace")
    return request_id, pkt_type, body


def rcon_command(host, port, password, command, timeout=5):
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(_pack(1, SERVERDATA_AUTH, password))
        request_id, _, _ = _read_packet(sock)
        if request_id == -1:
            raise RuntimeError("RCON authentication failed (bad password)")

        sock.sendall(_pack(2, SERVERDATA_EXECCOMMAND, command))
        _, _, body = _read_packet(sock)
        return body
