"""TCP RPC Client for Variant 22 matching data layer method signatures."""

import socket

from src.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    OP_CREATE_ANSWER,
    OP_CREATE_REQUEST,
    OP_CREATE_SESSION,
    OP_DELETE_ANSWER,
    OP_DELETE_REQUEST,
    OP_DELETE_SESSION,
    OP_GET_ALL_ANSWERS,
    OP_GET_ALL_REQUESTS,
    OP_GET_ALL_SESSIONS,
    OP_QUERY_JOIN,
    OP_UPDATE_ANSWER,
    OP_UPDATE_REQUEST,
    OP_UPDATE_SESSION,
    RESP_HEADER_SIZE,
    STATUS_ERROR,
    ZERO,
    ONE,
    TWO,
)
import src.protocol as proto


def _read_exact(sock, count):
    """Read exact count bytes from socket or raise IOError."""
    buf = bytearray()
    while len(buf) < count:
        chunk = sock.recv(count - len(buf))
        if len(chunk) == ZERO:
            raise ConnectionResetError("Connection closed prematurely")
        buf.extend(chunk)
    return bytes(buf)


class RPCClient:
    """Client implementing remote calls for all 13 data layer functions."""

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        """Initialize RPC client configuration."""
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        """Open TCP connection to RPC server."""
        if self.sock is None:
            self.sock = socket.create_connection((self.host, self.port))

    def close(self):
        """Close active TCP connection."""
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def __enter__(self):
        """Context manager entry point."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close()

    def _call(self, op_code, **params):
        """Execute RPC remote procedure call over TCP."""
        self.connect()
        xml_bytes = proto.serialize_request_xml(params)
        req_header = proto.encode_request_header(op_code, len(xml_bytes))
        self.sock.sendall(req_header + xml_bytes)

        resp_header = _read_exact(self.sock, RESP_HEADER_SIZE)
        resp_op, body_len = proto.decode_response_header(resp_header)
        body_bytes = _read_exact(self.sock, body_len)
        status, payload = proto.deserialize_response_xml(body_bytes)

        if status == STATUS_ERROR:
            raise RuntimeError(payload)
        return payload

    def create_session(self, uid, timestamp, locale, user_agent):
        """Call remote create_session procedure."""
        return self._call(
            OP_CREATE_SESSION,
            uid=uid,
            timestamp=timestamp,
            locale=locale,
            user_agent=user_agent
        )

    def delete_session(self, uid):
        """Call remote delete_session procedure."""
        return self._call(OP_DELETE_SESSION, uid=uid)

    def get_all_sessions(self):
        """Call remote get_all_sessions procedure."""
        return self._call(OP_GET_ALL_SESSIONS)

    def update_session(self, uid, timestamp=None, locale=None,
                       user_agent=None):
        """Call remote update_session procedure."""
        return self._call(
            OP_UPDATE_SESSION,
            uid=uid,
            timestamp=timestamp,
            locale=locale,
            user_agent=user_agent
        )

    def create_request(self, uid, timestamp, content, session, triggered):
        """Call remote create_request procedure."""
        return self._call(
            OP_CREATE_REQUEST,
            uid=uid,
            timestamp=timestamp,
            content=content,
            session=session,
            triggered=triggered
        )

    def delete_request(self, uid):
        """Call remote delete_request procedure."""
        return self._call(OP_DELETE_REQUEST, uid=uid)

    def get_all_requests(self):
        """Call remote get_all_requests procedure."""
        return self._call(OP_GET_ALL_REQUESTS)

    def update_request(self, uid, timestamp=None, content=None,
                       session=None, triggered=None):
        """Call remote update_request procedure."""
        return self._call(
            OP_UPDATE_REQUEST,
            uid=uid,
            timestamp=timestamp,
            content=content,
            session=session,
            triggered=triggered
        )

    def create_answer(self, uid, timestamp, output, status,
                      *extra, **kwargs):
        """Call remote create_answer procedure."""
        exc = kwargs.get("exception")
        req = kwargs.get("request")
        hit = kwargs.get("cache_hit")
        if len(extra) > ZERO:
            exc = extra[ZERO]
        if len(extra) > ONE:
            req = extra[ONE]
        if len(extra) > TWO:
            hit = extra[TWO]
        return self._call(
            OP_CREATE_ANSWER,
            uid=uid,
            timestamp=timestamp,
            output=output,
            status=status,
            exception=exc,
            request=req,
            cache_hit=hit
        )

    def delete_answer(self, uid):
        """Call remote delete_answer procedure."""
        return self._call(OP_DELETE_ANSWER, uid=uid)

    def get_all_answers(self):
        """Call remote get_all_answers procedure."""
        return self._call(OP_GET_ALL_ANSWERS)

    def update_answer(self, uid, *args, **kwargs):
        """Call remote update_answer procedure."""
        fields = [
            "timestamp", "output", "status",
            "exception", "request", "cache_hit"
        ]
        params = {k: None for k in fields}
        params.update(dict(zip(fields, args)))
        params.update(kwargs)
        params["uid"] = uid
        return self._call(OP_UPDATE_ANSWER, **params)

    def query_sessions_requests(self, now=None):
        """Call remote query_sessions_requests procedure."""
        return self._call(OP_QUERY_JOIN, now=now)
