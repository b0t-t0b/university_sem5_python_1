"""In-memory data layer using tuples for Variant 22."""

from collections import namedtuple
import time

from src.constants import (
    QUERY_TIME_WINDOW_SECONDS,
)

SessionRecord = namedtuple(
    "SessionRecord",
    ["uid", "timestamp", "locale", "user_agent"]
)

RequestRecord = namedtuple(
    "RequestRecord",
    ["uid", "timestamp", "content", "session", "triggered"]
)

AnswerRecord = namedtuple(
    "AnswerRecord",
    [
        "uid",
        "timestamp",
        "output",
        "status",
        "exception",
        "request",
        "cache_hit"
    ]
)

_SESSIONS = {}
_REQUESTS = {}
_ANSWERS = {}


def clear_all_data():
    """Clear all records from in-memory tables."""
    _SESSIONS.clear()
    _REQUESTS.clear()
    _ANSWERS.clear()


def create_session(uid, timestamp, locale, user_agent):
    """Create and store a new Session record tuple."""
    if uid in _SESSIONS:
        raise ValueError(f"Session with uid {uid} already exists")
    record = SessionRecord(
        int(uid), int(timestamp), str(locale), str(user_agent)
    )
    _SESSIONS[record.uid] = record
    return record


def delete_session(uid):
    """Delete Session record by uid if not referenced."""
    int_uid = int(uid)
    if int_uid not in _SESSIONS:
        raise KeyError(f"Session with uid {int_uid} not found")
    for req in _REQUESTS.values():
        if req.session == int_uid:
            raise ValueError(
                f"Cannot delete session {int_uid}: referenced by request"
            )
    del _SESSIONS[int_uid]
    return True


def get_all_sessions():
    """Return all Session record tuples."""
    return list(_SESSIONS.values())


def update_session(uid, timestamp=None, locale=None, user_agent=None):
    """Update Session record fields and return new record tuple."""
    int_uid = int(uid)
    if int_uid not in _SESSIONS:
        raise KeyError(f"Session with uid {int_uid} not found")
    current = _SESSIONS[int_uid]
    new_ts = current.timestamp if timestamp is None else int(timestamp)
    new_loc = current.locale if locale is None else str(locale)
    new_ua = current.user_agent if user_agent is None else str(user_agent)
    updated = SessionRecord(int_uid, new_ts, new_loc, new_ua)
    _SESSIONS[int_uid] = updated
    return updated


def create_request(uid, timestamp, content, session, triggered):
    """Create and store a new Request record tuple."""
    int_uid = int(uid)
    int_sess = int(session)
    if int_uid in _REQUESTS:
        raise ValueError(f"Request with uid {int_uid} already exists")
    if int_sess not in _SESSIONS:
        raise ValueError(f"Session with uid {int_sess} does not exist")
    record = RequestRecord(
        int_uid,
        int(timestamp),
        str(content),
        int_sess,
        int(triggered)
    )
    _REQUESTS[int_uid] = record
    return record


def delete_request(uid):
    """Delete Request record by uid if not referenced."""
    int_uid = int(uid)
    if int_uid not in _REQUESTS:
        raise KeyError(f"Request with uid {int_uid} not found")
    for ans in _ANSWERS.values():
        if ans.request == int_uid:
            raise ValueError(
                f"Cannot delete request {int_uid}: referenced by answer"
            )
    del _REQUESTS[int_uid]
    return True


def get_all_requests():
    """Return all Request record tuples."""
    return list(_REQUESTS.values())


def update_request(uid, timestamp=None, content=None,
                   session=None, triggered=None):
    """Update Request record fields and return new record tuple."""
    int_uid = int(uid)
    if int_uid not in _REQUESTS:
        raise KeyError(f"Request with uid {int_uid} not found")
    cur = _REQUESTS[int_uid]
    new_sess = cur.session if session is None else int(session)
    if new_sess not in _SESSIONS:
        raise ValueError(f"Session with uid {new_sess} does not exist")
    new_ts = cur.timestamp if timestamp is None else int(timestamp)
    new_cnt = cur.content if content is None else str(content)
    new_trig = cur.triggered if triggered is None else int(triggered)
    updated = RequestRecord(int_uid, new_ts, new_cnt, new_sess, new_trig)
    _REQUESTS[int_uid] = updated
    return updated


def create_answer(uid, timestamp, output, status,
                  exception, request, cache_hit):
    """Create and store a new Answer record tuple."""
    int_uid = int(uid)
    int_req = int(request)
    if int_uid in _ANSWERS:
        raise ValueError(f"Answer with uid {int_uid} already exists")
    if int_req not in _REQUESTS:
        raise ValueError(f"Request with uid {int_req} does not exist")
    record = AnswerRecord(
        int_uid,
        int(timestamp),
        str(output),
        str(status),
        str(exception),
        int_req,
        int(cache_hit)
    )
    _ANSWERS[int_uid] = record
    return record


def delete_answer(uid):
    """Delete Answer record by uid."""
    int_uid = int(uid)
    if int_uid not in _ANSWERS:
        raise KeyError(f"Answer with uid {int_uid} not found")
    del _ANSWERS[int_uid]
    return True


def get_all_answers():
    """Return all Answer record tuples."""
    return list(_ANSWERS.values())


def update_answer(uid, timestamp=None, output=None, status=None,
                  exception=None, request=None, cache_hit=None):
    """Update Answer record fields and return new record tuple."""
    int_uid = int(uid)
    if int_uid not in _ANSWERS:
        raise KeyError(f"Answer with uid {int_uid} not found")
    cur = _ANSWERS[int_uid]
    new_req = cur.request if request is None else int(request)
    if new_req not in _REQUESTS:
        raise ValueError(f"Request with uid {new_req} does not exist")
    new_ts = cur.timestamp if timestamp is None else int(timestamp)
    new_out = cur.output if output is None else str(output)
    new_st = cur.status if status is None else str(status)
    new_exc = cur.exception if exception is None else str(exception)
    new_ch = cur.cache_hit if cache_hit is None else int(cache_hit)
    updated = AnswerRecord(
        int_uid, new_ts, new_out, new_st, new_exc, new_req, new_ch
    )
    _ANSWERS[int_uid] = updated
    return updated


def query_sessions_requests(now=None):
    """
    Execute relational algebra query:
    pi_{R.content, S.locale} (
        (sigma_{S.timestamp >= now - 6 min} (S))
        RIGHT_OUTER_JOIN_{S.uid = R.session}
        R
    )
    """
    ref_time = int(time.time()) if now is None else int(now)
    threshold = ref_time - QUERY_TIME_WINDOW_SECONDS
    filtered_sessions = {
        s.uid: s for s in _SESSIONS.values()
        if s.timestamp >= threshold
    }
    result = []
    for req in _REQUESTS.values():
        matched_sess = filtered_sessions.get(req.session)
        locale_val = None if matched_sess is None else matched_sess.locale
        result.append((req.content, locale_val))
    return result
