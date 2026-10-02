"""TCP RPC Server implementation conforming to Table 22 specification."""

from datetime import datetime
import socketserver
import threading

from src.constants import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    ENCODING,
    JOURNAL_FILE,
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
    REQ_HEADER_SIZE,
    STATUS_ERROR,
    STATUS_SUCCESS,
    ZERO,
)
import src.data_layer as dl
import src.protocol as proto

_JOURNAL_LOCK = threading.Lock()


def log_rpc_response(client_addr, op_code, body_bytes,
                     journal_path=JOURNAL_FILE):
    """Append serialized RPC response record to journal log file."""
    now_str = datetime.now().isoformat()
    body_text = body_bytes.decode(ENCODING, errors="replace")
    record = (
        f"[{now_str}] Client: {client_addr} | OpCode: {op_code} | "
        f"Length: {len(body_bytes)} | Body: {body_text}\n"
    )
    with _JOURNAL_LOCK:
        with open(journal_path, "a", encoding=ENCODING) as file_obj:
            file_obj.write(record)


def _recv_exact(sock, count):
    """Read exact count bytes from TCP socket or return None on EOF."""
    buffer = bytearray()
    while len(buffer) < count:
        chunk = sock.recv(count - len(buffer))
        if len(chunk) == ZERO:
            return None
        buffer.extend(chunk)
    return bytes(buffer)


def _dispatch_session(op_code, p):
    """Dispatch session-related operations."""
    if op_code == OP_CREATE_SESSION:
        return dl.create_session(
            p["uid"], p["timestamp"], p["locale"], p["user_agent"]
        )
    if op_code == OP_DELETE_SESSION:
        return dl.delete_session(p["uid"])
    if op_code == OP_GET_ALL_SESSIONS:
        return dl.get_all_sessions()
    if op_code == OP_UPDATE_SESSION:
        return dl.update_session(
            p["uid"], p.get("timestamp"), p.get("locale"),
            p.get("user_agent")
        )
    return None


def _dispatch_request(op_code, p):
    """Dispatch request-related operations."""
    if op_code == OP_CREATE_REQUEST:
        return dl.create_request(
            p["uid"], p["timestamp"], p["content"],
            p["session"], p["triggered"]
        )
    if op_code == OP_DELETE_REQUEST:
        return dl.delete_request(p["uid"])
    if op_code == OP_GET_ALL_REQUESTS:
        return dl.get_all_requests()
    if op_code == OP_UPDATE_REQUEST:
        return dl.update_request(
            p["uid"], p.get("timestamp"), p.get("content"),
            p.get("session"), p.get("triggered")
        )
    return None


def _dispatch_answer(op_code, p):
    """Dispatch answer and join operations."""
    if op_code == OP_CREATE_ANSWER:
        return dl.create_answer(
            p["uid"], p["timestamp"], p["output"], p["status"],
            p["exception"], p["request"], p["cache_hit"]
        )
    if op_code == OP_DELETE_ANSWER:
        return dl.delete_answer(p["uid"])
    if op_code == OP_GET_ALL_ANSWERS:
        return dl.get_all_answers()
    if op_code == OP_UPDATE_ANSWER:
        return dl.update_answer(
            p["uid"], p.get("timestamp"), p.get("output"),
            p.get("status"), p.get("exception"),
            p.get("request"), p.get("cache_hit")
        )
    if op_code == OP_QUERY_JOIN:
        return dl.query_sessions_requests(p.get("now"))
    raise ValueError(f"Unknown operation code {op_code}")


def dispatch_rpc_call(op_code, params):
    """Route operation code to appropriate data layer function."""
    if op_code in (
        OP_CREATE_SESSION, OP_DELETE_SESSION,
        OP_GET_ALL_SESSIONS, OP_UPDATE_SESSION
    ):
        return _dispatch_session(op_code, params)
    if op_code in (
        OP_CREATE_REQUEST, OP_DELETE_REQUEST,
        OP_GET_ALL_REQUESTS, OP_UPDATE_REQUEST
    ):
        return _dispatch_request(op_code, params)
    if op_code in (
        OP_CREATE_ANSWER, OP_DELETE_ANSWER,
        OP_GET_ALL_ANSWERS, OP_UPDATE_ANSWER,
        OP_QUERY_JOIN
    ):
        return _dispatch_answer(op_code, params)
    raise ValueError(f"Unrecognized operation {op_code}")


class RPCRequestHandler(socketserver.BaseRequestHandler):
    """Handles incoming TCP RPC requests."""

    def handle(self):
        """Process messages on persistent client connection."""
        addr_str = f"{self.client_address[ZERO]}:{self.client_address[1]}"
        while True:
            raw_header = _recv_exact(self.request, REQ_HEADER_SIZE)
            if raw_header is None:
                break
            op_code, body_len = proto.decode_request_header(raw_header)
            raw_body = _recv_exact(self.request, body_len)
            if raw_body is None:
                break
            try:
                params = proto.deserialize_request_xml(raw_body)
                res = dispatch_rpc_call(op_code, params)
                resp_xml = proto.serialize_response_xml(
                    STATUS_SUCCESS, result=res
                )
            except Exception as exc:
                resp_xml = proto.serialize_response_xml(
                    STATUS_ERROR, error=str(exc)
                )
            journal_path = getattr(
                self.server, "journal_file", JOURNAL_FILE
            )
            log_rpc_response(
                addr_str, op_code, resp_xml, journal_path=journal_path
            )
            resp_header = proto.encode_response_header(
                op_code, len(resp_xml)
            )
            self.request.sendall(resp_header + resp_xml)


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Multithreaded TCP server allowing address reuse."""
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, handler_cls,
                 journal_file=JOURNAL_FILE):
        """Initialize server with custom journal path."""
        super().__init__(server_address, handler_cls)
        self.journal_file = journal_file


def run_standalone_server(host=DEFAULT_HOST, port=DEFAULT_PORT,
                          journal_file=JOURNAL_FILE):
    """Run RPC server in main thread until interrupted."""
    with ThreadedTCPServer((host, port), RPCRequestHandler,
                           journal_file=journal_file) as srv:
        print(f"RPC Server listening on {host}:{port}")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down RPC server.")


if __name__ == "__main__":
    run_standalone_server()
