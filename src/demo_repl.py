"""Interactive demonstration script for Stage 1 data layer."""

import time
import src.data_layer as dl
from src.repl import execute_line


def run_session_demo():
    """Demonstrate Session operations and error handling."""
    print("--- Session Operations ---")
    print(execute_line("add-session 1 1700000000 ru-RU Chrome/120"))
    print(execute_line("add-session 2 1700000100 en-US Firefox/121"))
    print(execute_line("list-sessions"))
    print(execute_line("update-session 1 - ru-RU Chrome/122"))
    print(execute_line("list-sessions"))
    try:
        execute_line("add-session 1 1700000200 fr-FR Safari/17")
    except ValueError as err:
        print(f"Expected duplicate error: {err}")


def run_request_demo():
    """Demonstrate Request operations and foreign key checks."""
    print("\n--- Request Operations ---")
    print(execute_line("add-request 10 1700000050 'SELECT 1' 1 1"))
    print(execute_line("add-request 20 1700000150 'UPDATE user' 2 0"))
    print(execute_line("list-requests"))
    print(execute_line("update-request 10 - 'SELECT 2' - -"))
    print(execute_line("list-requests"))
    try:
        execute_line("add-request 30 1700000200 'INSERT' 999 1")
    except ValueError as err:
        print(f"Expected FK violation: {err}")


def run_answer_demo():
    """Demonstrate Answer operations and constraints."""
    print("\n--- Answer Operations ---")
    print(execute_line("add-answer 100 1700000060 ok 200 None 10 1"))
    print(execute_line("add-answer 200 1700000160 done 200 None 20 0"))
    print(execute_line("list-answers"))
    print(execute_line("update-answer 100 - cached 200 None - 1"))
    print(execute_line("list-answers"))
    try:
        execute_line("add-answer 300 1700000200 fail 500 Err 999 0")
    except ValueError as err:
        print(f"Expected FK violation: {err}")


def run_relational_query_demo():
    """Demonstrate relational algebra query with right outer join."""
    print("\n--- Relational Algebra Query Demonstration ---")
    dl.clear_all_data()
    now_ts = int(time.time())
    ts_recent = now_ts - 120
    ts_old = now_ts - 600

    dl.create_session(1, ts_recent, "ru-RU", "Browser-A")
    dl.create_session(2, ts_old, "en-US", "Browser-B")

    dl.create_request(11, ts_recent, "Query Recent Sess", 1, 1)
    dl.create_request(22, ts_old, "Query Old Sess", 2, 0)

    print("Created Session 1 (recent: now - 2 min, ru-RU)")
    print("Created Session 2 (old: now - 10 min, en-US)")
    print("Created Request 11 (references Session 1)")
    print("Created Request 22 (references Session 2)")

    out = execute_line(f"query-join {now_ts}")
    print(out)


def run_deletion_demo():
    """Demonstrate deletion and reference integrity protection."""
    print("\n--- Deletion and Referential Integrity ---")
    try:
        execute_line("delete-session 1")
    except ValueError as err:
        print(f"Expected reference integrity error: {err}")

    dl.create_answer(501, 1700000000, "out", "200", "None", 11, 1)
    try:
        execute_line("delete-request 11")
    except ValueError as err:
        print(f"Expected answer reference error: {err}")

    print(execute_line("delete-answer 501"))
    print(execute_line("delete-request 11"))
    print(execute_line("delete-session 1"))
    print(execute_line("list-sessions"))


def main():
    """Run full Stage 1 demo."""
    dl.clear_all_data()
    run_session_demo()
    run_request_demo()
    run_answer_demo()
    run_relational_query_demo()
    run_deletion_demo()
    print("\nStage 1 Demonstration Completed Successfully.")


if __name__ == "__main__":
    main()
