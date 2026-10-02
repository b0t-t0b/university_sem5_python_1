"""Interactive REPL for the in-memory data layer (Variant 22)."""

import shlex
import sys
from src.constants import (
    ONE,
    TWO,
    THREE,
    FOUR,
    FIVE,
    SIX,
    SEVEN,
    EIGHT,
    ZERO,
    REPL_PROMPT,
    REPL_EXIT_CMD,
    REPL_HELP_CMD,
)
import src.data_layer as dl


def parse_opt(val):
    """Return parsed value or None if placeholder hyphen provided."""
    if val == "-":
        return None
    return val


def handle_session_cmd(parts):
    """Process session-related REPL commands."""
    cmd = parts[ZERO]
    if cmd == "add-session":
        if len(parts) != FIVE:
            raise ValueError(
                "Usage: add-session <uid> <timestamp> <locale> <user_agent>"
            )
        rec = dl.create_session(
            parts[ONE], parts[TWO], parts[THREE], parts[FOUR]
        )
        return f"Session created: {rec}"
    if cmd == "list-sessions":
        items = dl.get_all_sessions()
        return f"Sessions ({len(items)}): {items}"
    if cmd == "delete-session":
        if len(parts) != TWO:
            raise ValueError("Usage: delete-session <uid>")
        dl.delete_session(parts[ONE])
        return f"Session {parts[ONE]} deleted"
    if cmd == "update-session":
        if len(parts) != FIVE:
            raise ValueError(
                "Usage: update-session <uid> <ts|-> <loc|-> <ua|->"
            )
        rec = dl.update_session(
            parts[ONE],
            parse_opt(parts[TWO]),
            parse_opt(parts[THREE]),
            parse_opt(parts[FOUR])
        )
        return f"Session updated: {rec}"
    return None


def handle_request_cmd(parts):
    """Process request-related REPL commands."""
    cmd = parts[ZERO]
    if cmd == "add-request":
        if len(parts) != SIX:
            raise ValueError(
                "Usage: add-request <uid> <timestamp> <content> "
                "<session> <triggered>"
            )
        rec = dl.create_request(
            parts[ONE], parts[TWO], parts[THREE], parts[FOUR], parts[FIVE]
        )
        return f"Request created: {rec}"
    if cmd == "list-requests":
        items = dl.get_all_requests()
        return f"Requests ({len(items)}): {items}"
    if cmd == "delete-request":
        if len(parts) != TWO:
            raise ValueError("Usage: delete-request <uid>")
        dl.delete_request(parts[ONE])
        return f"Request {parts[ONE]} deleted"
    if cmd == "update-request":
        if len(parts) != SIX:
            raise ValueError(
                "Usage: update-request <uid> <ts|-> <cnt|-> <sess|-> <trig|->"
            )
        rec = dl.update_request(
            parts[ONE],
            parse_opt(parts[TWO]),
            parse_opt(parts[THREE]),
            parse_opt(parts[FOUR]),
            parse_opt(parts[FIVE])
        )
        return f"Request updated: {rec}"
    return None


def handle_answer_cmd(parts):
    """Process answer-related REPL commands."""
    cmd = parts[ZERO]
    if cmd == "add-answer":
        if len(parts) != EIGHT:
            raise ValueError(
                "Usage: add-answer <uid> <ts> <out> <st> <exc> <req> <hit>"
            )
        rec = dl.create_answer(
            parts[ONE], parts[TWO], parts[THREE], parts[FOUR],
            parts[FIVE], parts[SIX], parts[SEVEN]
        )
        return f"Answer created: {rec}"
    if cmd == "list-answers":
        items = dl.get_all_answers()
        return f"Answers ({len(items)}): {items}"
    if cmd == "delete-answer":
        if len(parts) != TWO:
            raise ValueError("Usage: delete-answer <uid>")
        dl.delete_answer(parts[ONE])
        return f"Answer {parts[ONE]} deleted"
    if cmd == "update-answer":
        if len(parts) != EIGHT:
            raise ValueError(
                "Usage: update-answer <uid> <ts|-> <out|-> <st|-> "
                "<exc|-> <req|-> <hit|->"
            )
        rec = dl.update_answer(
            parts[ONE],
            parse_opt(parts[TWO]),
            parse_opt(parts[THREE]),
            parse_opt(parts[FOUR]),
            parse_opt(parts[FIVE]),
            parse_opt(parts[SIX]),
            parse_opt(parts[SEVEN])
        )
        return f"Answer updated: {rec}"
    return None


def print_help():
    """Return summary help string."""
    return (
        "Commands:\n"
        "  add-session <uid> <ts> <locale> <ua>\n"
        "  list-sessions\n"
        "  update-session <uid> <ts|-> <loc|-> <ua|->\n"
        "  delete-session <uid>\n"
        "  add-request <uid> <ts> <content> <session> <triggered>\n"
        "  list-requests\n"
        "  update-request <uid> <ts|-> <cnt|-> <sess|-> <trig|->\n"
        "  delete-request <uid>\n"
        "  add-answer <uid> <ts> <out> <st> <exc> <req> <hit>\n"
        "  list-answers\n"
        "  update-answer <uid> <ts|-> <out|-> <st|-> <exc|-> <req|-> <hit|->\n"
        "  delete-answer <uid>\n"
        "  query-join [now]\n"
        "  clear\n"
        "  help\n"
        "  exit"
    )


def execute_line(line):
    """Execute a single command line and return string result."""
    parts = shlex.split(line)
    if len(parts) == ZERO:
        return ""
    cmd = parts[ZERO]
    if cmd == REPL_HELP_CMD:
        return print_help()
    if cmd == "clear":
        dl.clear_all_data()
        return "All tables cleared"
    if cmd == "query-join":
        now_val = None if len(parts) == ONE else int(parts[ONE])
        res = dl.query_sessions_requests(now=now_val)
        return f"Query result (content, locale) ({len(res)}): {res}"
    for handler in (handle_session_cmd, handle_request_cmd, handle_answer_cmd):
        out = handler(parts)
        if out is not None:
            return out
    return f"Unknown command: {cmd}. Type 'help' for instructions."


def run_repl():
    """Run interactive REPL loop."""
    print("Variant 22 In-Memory Data Layer REPL. Type 'help' or 'exit'.")
    while True:
        try:
            raw = input(REPL_PROMPT).strip()
            if raw == REPL_EXIT_CMD or raw == "quit":
                print("Exiting REPL.")
                break
            if len(raw) == ZERO:
                continue
            output = execute_line(raw)
            if output:
                print(output)
        except (ValueError, KeyError, IndexError) as err:
            print(f"Error: {err}")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting REPL.")
            break


if __name__ == "__main__":
    if len(sys.argv) > ONE and sys.argv[ONE] == "--batch":
        for script_line in sys.stdin:
            script_line = script_line.strip()
            if script_line:
                print(f"> {script_line}")
                try:
                    res_msg = execute_line(script_line)
                    if res_msg:
                        print(res_msg)
                except Exception as ex:
                    print(f"Error: {ex}")
    else:
        run_repl()
