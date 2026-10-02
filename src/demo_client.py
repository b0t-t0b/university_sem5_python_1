"""Demonstration of TCP RPC Server and Client for Stage 2."""

import os
import threading
import time

from src.client import RPCClient
from src.constants import (
    DEFAULT_HOST,
    JOURNAL_FILE,
    ZERO,
)
import src.data_layer as dl
from src.server import ThreadedTCPServer, RPCRequestHandler


def _run_server_thread(srv):
    """Serve requests until server shutdown requested."""
    srv.serve_forever()


def _demo_sessions(client):
    """Demonstrate Session operations over RPC."""
    print("1. Creating sessions via RPC...")
    s1 = client.create_session(1, 1700000000, "ru-RU", "Mozilla/5.0")
    s2 = client.create_session(2, 1700000100, "en-US", "Gecko/20100101")
    print(f"Created Session 1: {s1}")
    print(f"Created Session 2: {s2}")

    print("2. Fetching all sessions via RPC...")
    sessions = client.get_all_sessions()
    print(f"All Sessions ({len(sessions)}): {sessions}")

    print("3. Updating session 1 via RPC...")
    s1_upd = client.update_session(1, user_agent="Mozilla/5.1")
    print(f"Updated Session 1: {s1_upd}")


def _demo_requests(client):
    """Demonstrate Request operations over RPC."""
    print("4. Creating requests via RPC...")
    r1 = client.create_request(10, 1700000050, "GET /api/v1", 1, 1)
    r2 = client.create_request(20, 1700000150, "POST /auth", 2, 0)
    print(f"Created Request 10: {r1}")
    print(f"Created Request 20: {r2}")

    print("5. Fetching all requests via RPC...")
    requests = client.get_all_requests()
    print(f"All Requests ({len(requests)}): {requests}")

    print("6. Updating request 10 via RPC...")
    r1_upd = client.update_request(10, content="GET /api/v2")
    print(f"Updated Request 10: {r1_upd}")


def _demo_answers(client):
    """Demonstrate Answer operations over RPC."""
    print("7. Creating answers via RPC...")
    a1 = client.create_answer(100, 1700000060, "OK", "200", "None", 10, 1)
    a2 = client.create_answer(200, 1700000160, "Created", "201", "None", 20, 0)
    print(f"Created Answer 100: {a1}")
    print(f"Created Answer 200: {a2}")

    print("8. Fetching all answers via RPC...")
    answers = client.get_all_answers()
    print(f"All Answers ({len(answers)}): {answers}")

    print("9. Updating answer 100 via RPC...")
    a1_upd = client.update_answer(100, output="Cached OK")
    print(f"Updated Answer 100: {a1_upd}")


def _demo_query_and_delete(client):
    """Demonstrate relational query and deletions over RPC."""
    now_ts = int(time.time())
    client.update_session(1, timestamp=now_ts - 60)
    client.update_session(2, timestamp=now_ts - 600)

    print("10. Relational query (content, locale) via RPC...")
    join_res = client.query_sessions_requests(now=now_ts)
    print(f"Query Result: {join_res}")

    print("11. Deletion with error handling via RPC...")
    try:
        client.delete_session(1)
    except RuntimeError as exc:
        print(f"Expected deletion rejection: {exc}")

    print("12. Deleting answer 100 via RPC...")
    print(f"Deleted answer 100: {client.delete_answer(100)}")
    print("13. Deleting request 10 via RPC...")
    print(f"Deleted request 10: {client.delete_request(10)}")
    print("14. Deleting session 1 via RPC...")
    print(f"Deleted session 1: {client.delete_session(1)}")


def run_demo():
    """Run full Stage 2 RPC client/server demonstration."""
    dl.clear_all_data()
    if os.path.exists(JOURNAL_FILE):
        os.remove(JOURNAL_FILE)

    server = ThreadedTCPServer(
        (DEFAULT_HOST, ZERO), RPCRequestHandler, journal_file=JOURNAL_FILE
    )
    actual_port = server.server_address[1]
    thread = threading.Thread(
        target=_run_server_thread, args=(server,), daemon=True
    )
    thread.start()
    print(f"Test RPC Server started on port {actual_port}")

    try:
        with RPCClient(host=DEFAULT_HOST, port=actual_port) as client:
            _demo_sessions(client)
            _demo_requests(client)
            _demo_answers(client)
            _demo_query_and_delete(client)

        print("\n--- Journal Log Verification (first 5 records) ---")
        if os.path.exists(JOURNAL_FILE):
            with open(JOURNAL_FILE, "r", encoding="utf-8") as f_obj:
                lines = f_obj.readlines()
            print(f"Total journal entries: {len(lines)}")
            for entry in lines[:5]:
                print(entry.strip())
    finally:
        server.shutdown()
        server.server_close()
        print("\nTest RPC Server stopped successfully.")


if __name__ == "__main__":
    run_demo()
