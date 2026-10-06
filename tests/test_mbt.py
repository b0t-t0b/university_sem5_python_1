"""Model-Based Testing (MBT) of TCP RPC service using Hypothesis."""

import threading
from hypothesis import settings
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    multiple,
    rule,
    run_state_machine_as_test,
)
import hypothesis.strategies as st

from src.client import RPCClient
from src.constants import (
    DEFAULT_HOST,
    QUERY_TIME_WINDOW_SECONDS,
    ZERO,
    ONE,
    TWO,
)
import src.data_layer as dl
from src.server import RPCRequestHandler, ThreadedTCPServer

_server = None
_server_thread = None
_server_port = 0


def setup_module():
    """Start shared background TCP RPC server for MBT testing."""
    global _server, _server_thread, _server_port
    _server = ThreadedTCPServer(
        (DEFAULT_HOST, ZERO), RPCRequestHandler
    )
    _server_port = _server.server_address[1]
    _server_thread = threading.Thread(
        target=_server.serve_forever, daemon=True
    )
    _server_thread.start()


def teardown_module():
    """Shut down shared background TCP RPC server after MBT testing."""
    if _server is not None:
        _server.shutdown()
        _server.server_close()


class ReferenceModel:
    """Independent reference in-memory data model for verification."""

    def __init__(self):
        """Initialize empty entity dictionaries."""
        self.sessions = {}
        self.requests = {}
        self.answers = {}

    def clear(self):
        """Reset reference state."""
        self.sessions.clear()
        self.requests.clear()
        self.answers.clear()

    def create_session(self, uid, ts, loc, ua):
        """Model create session."""
        if uid in self.sessions:
            raise ValueError(f"Session {uid} exists")
        rec = (int(uid), int(ts), str(loc), str(ua))
        self.sessions[uid] = rec
        return rec

    def delete_session(self, uid):
        """Model delete session with FK check."""
        if uid not in self.sessions:
            raise KeyError(f"Session {uid} not found")
        for req in self.requests.values():
            if req[3] == uid:
                raise ValueError("Referenced by request")
        del self.sessions[uid]
        return True

    def get_all_sessions(self):
        """Model get all sessions."""
        return list(self.sessions.values())

    def update_session(self, uid, timestamp=None, locale=None,
                       user_agent=None):
        """Model update session."""
        if uid not in self.sessions:
            raise KeyError(f"Session {uid} not found")
        cur = self.sessions[uid]
        new_ts = cur[1] if timestamp is None else int(timestamp)
        new_loc = cur[2] if locale is None else str(locale)
        new_ua = cur[3] if user_agent is None else str(user_agent)
        rec = (int(uid), new_ts, new_loc, new_ua)
        self.sessions[uid] = rec
        return rec

    def create_request(self, uid, ts, cnt, sess, trig):
        """Model create request with FK check."""
        if uid in self.requests:
            raise ValueError(f"Request {uid} exists")
        if sess not in self.sessions:
            raise ValueError(f"Session {sess} missing")
        rec = (int(uid), int(ts), str(cnt), int(sess), int(trig))
        self.requests[uid] = rec
        return rec

    def delete_request(self, uid):
        """Model delete request with FK check."""
        if uid not in self.requests:
            raise KeyError(f"Request {uid} not found")
        for ans in self.answers.values():
            if ans[5] == uid:
                raise ValueError("Referenced by answer")
        del self.requests[uid]
        return True

    def get_all_requests(self):
        """Model get all requests."""
        return list(self.requests.values())

    def update_request(self, uid, timestamp=None, content=None,
                       session=None, triggered=None):
        """Model update request."""
        if uid not in self.requests:
            raise KeyError(f"Request {uid} not found")
        cur = self.requests[uid]
        new_sess = cur[3] if session is None else int(session)
        if new_sess not in self.sessions:
            raise ValueError(f"Session {new_sess} missing")
        new_ts = cur[1] if timestamp is None else int(timestamp)
        new_cnt = cur[2] if content is None else str(content)
        new_trig = cur[4] if triggered is None else int(triggered)
        rec = (int(uid), new_ts, new_cnt, new_sess, new_trig)
        self.requests[uid] = rec
        return rec

    def create_answer(self, uid, ts, out, st_code, *extra, **kwargs):
        """Model create answer with FK check."""
        exc = kwargs.get("exception")
        req = kwargs.get("request")
        hit = kwargs.get("cache_hit")
        if len(extra) > ZERO:
            exc = extra[ZERO]
        if len(extra) > ONE:
            req = extra[ONE]
        if len(extra) > TWO:
            hit = extra[TWO]
        if uid in self.answers:
            raise ValueError(f"Answer {uid} exists")
        if req not in self.requests:
            raise ValueError(f"Request {req} missing")
        rec = (
            int(uid), int(ts), str(out), str(st_code),
            str(exc), int(req), int(hit)
        )
        self.answers[uid] = rec
        return rec

    def delete_answer(self, uid):
        """Model delete answer."""
        if uid not in self.answers:
            raise KeyError(f"Answer {uid} not found")
        del self.answers[uid]
        return True

    def get_all_answers(self):
        """Model get all answers."""
        return list(self.answers.values())

    def _merge(self, cur_val, new_val, cast_fn):
        """Cast new_val if given, otherwise keep cur_val."""
        return cur_val if new_val is None else cast_fn(new_val)

    def update_answer(self, uid, *args, **kwargs):
        """Model update answer."""
        if uid not in self.answers:
            raise KeyError(f"Answer {uid} not found")
        cur = self.answers[uid]
        fields = [
            "timestamp", "output", "status",
            "exception", "request", "cache_hit"
        ]
        vals = dict(zip(fields, args))
        vals.update(kwargs)
        req_val = vals.get("request")
        new_req = cur[5] if req_val is None else int(req_val)
        if new_req not in self.requests:
            raise ValueError(f"Request {new_req} missing")
        rec = (
            int(uid),
            self._merge(cur[1], vals.get("timestamp"), int),
            self._merge(cur[2], vals.get("output"), str),
            self._merge(cur[3], vals.get("status"), str),
            self._merge(cur[4], vals.get("exception"), str),
            new_req,
            self._merge(cur[6], vals.get("cache_hit"), int),
        )
        self.answers[uid] = rec
        return rec

    def query_sessions_requests(self, now):
        """Model relational algebra query."""
        thresh = int(now) - QUERY_TIME_WINDOW_SECONDS
        filtered = {
            s[0]: s for s in self.sessions.values()
            if s[1] >= thresh
        }
        res = []
        for req in self.requests.values():
            s_match = filtered.get(req[3])
            loc = None if s_match is None else s_match[2]
            res.append((req[2], loc))
        return res


class RPCModelComparison(RuleBasedStateMachine):
    """Hypothesis state machine comparing RPC server to reference model."""

    sessions = Bundle("sessions")
    requests = Bundle("requests")
    answers = Bundle("answers")

    def __init__(self):
        """Initialize state machine run."""
        super().__init__()
        self.model = ReferenceModel()
        self.client = RPCClient(host=DEFAULT_HOST, port=_server_port)
        self.client.connect()
        dl.clear_all_data()
        self.model.clear()

    def teardown(self):
        """Clean up client socket after run."""
        self.client.close()

    @rule(
        target=sessions,
        uid=st.integers(min_value=1, max_value=8),
        ts=st.integers(min_value=1000, max_value=2000),
        loc=st.sampled_from(["ru", "en", "kz"]),
        ua=st.sampled_from(["Chrome", "Safari", "Edge"])
    )
    def r_create_session(self, uid, ts, loc, ua):
        """Test create_session method over RPC."""
        expected_err = False
        try:
            self.model.create_session(uid, ts, loc, ua)
        except (ValueError, KeyError):
            expected_err = True
        try:
            rec = self.client.create_session(uid, ts, loc, ua)
            assert not expected_err
            assert rec[0] == uid
            assert rec[1] == ts
            assert rec[2] == loc
            assert rec[3] == ua
            return uid
        except RuntimeError:
            assert expected_err
            return multiple()

    @rule(uid=st.integers(min_value=1, max_value=8))
    def r_delete_session(self, uid):
        """Test delete_session method over RPC."""
        expected_err = False
        try:
            self.model.delete_session(uid)
        except (ValueError, KeyError):
            expected_err = True
        try:
            res = self.client.delete_session(uid)
            assert not expected_err
            assert res is True
        except RuntimeError:
            assert expected_err

    @rule()
    def r_get_all_sessions(self):
        """Test get_all_sessions method over RPC."""
        expected = sorted(self.model.get_all_sessions())
        actual = sorted(self.client.get_all_sessions())
        assert actual == expected

    @rule(
        uid=st.integers(min_value=1, max_value=8),
        ts=st.one_of(st.none(), st.integers(min_value=1000, max_value=2000)),
        loc=st.one_of(st.none(), st.sampled_from(["ru-mod", "en-mod"])),
        ua=st.one_of(st.none(), st.sampled_from(["Chrome10", "Safari10"]))
    )
    def r_update_session(self, uid, ts, loc, ua):
        """Test update_session method over RPC."""
        expected_err = False
        try:
            self.model.update_session(
                uid, timestamp=ts, locale=loc, user_agent=ua
            )
        except (ValueError, KeyError):
            expected_err = True
        try:
            rec = self.client.update_session(
                uid, timestamp=ts, locale=loc, user_agent=ua
            )
            assert not expected_err
            if loc is not None:
                assert rec[2] == loc
        except RuntimeError:
            assert expected_err

    @rule(
        target=requests,
        uid=st.integers(min_value=1, max_value=8),
        ts=st.integers(min_value=1000, max_value=2000),
        cnt=st.sampled_from(["reqA", "reqB"]),
        sess=st.integers(min_value=1, max_value=8),
        trig=st.integers(min_value=0, max_value=1)
    )
    def r_create_request(self, uid, ts, cnt, sess, trig):
        """Test create_request method over RPC."""
        expected_err = False
        try:
            self.model.create_request(uid, ts, cnt, sess, trig)
        except (ValueError, KeyError):
            expected_err = True
        try:
            rec = self.client.create_request(uid, ts, cnt, sess, trig)
            assert not expected_err
            assert rec[0] == uid
            assert rec[3] == sess
            return uid
        except RuntimeError:
            assert expected_err
            return multiple()

    @rule(uid=st.integers(min_value=1, max_value=8))
    def r_delete_request(self, uid):
        """Test delete_request method over RPC."""
        expected_err = False
        try:
            self.model.delete_request(uid)
        except (ValueError, KeyError):
            expected_err = True
        try:
            res = self.client.delete_request(uid)
            assert not expected_err
            assert res is True
        except RuntimeError:
            assert expected_err

    @rule()
    def r_get_all_requests(self):
        """Test get_all_requests method over RPC."""
        expected = sorted(self.model.get_all_requests())
        actual = sorted(self.client.get_all_requests())
        assert actual == expected

    @rule(
        uid=st.integers(min_value=1, max_value=8),
        ts=st.one_of(st.none(), st.integers(min_value=1000, max_value=2000)),
        cnt=st.one_of(st.none(), st.sampled_from(["reqA", "reqB"])),
        sess=st.one_of(st.none(), st.integers(min_value=1, max_value=8)),
        trig=st.one_of(st.none(), st.integers(min_value=0, max_value=1))
    )
    def r_update_request(self, uid, ts, cnt, sess, trig):
        """Test update_request method over RPC."""
        expected_err = False
        try:
            self.model.update_request(
                uid, timestamp=ts, content=cnt, session=sess, triggered=trig
            )
        except (ValueError, KeyError):
            expected_err = True
        try:
            rec = self.client.update_request(
                uid, timestamp=ts, content=cnt, session=sess, triggered=trig
            )
            assert not expected_err
            if cnt is not None:
                assert rec[2] == cnt
        except RuntimeError:
            assert expected_err

    @rule(
        target=answers,
        uid=st.integers(min_value=1, max_value=8),
        ts=st.integers(min_value=1000, max_value=2000),
        req=st.integers(min_value=1, max_value=8),
        st_code=st.sampled_from(["200", "500"])
    )
    def r_create_answer(self, uid, ts, req, st_code):
        """Test create_answer method over RPC."""
        expected_err = False
        out = "out"
        exc = "None"
        hit = 1
        try:
            self.model.create_answer(uid, ts, out, st_code, exc, req, hit)
        except (ValueError, KeyError):
            expected_err = True
        try:
            rec = self.client.create_answer(
                uid, ts, out, st_code, exc, req, hit
            )
            assert not expected_err
            assert rec[0] == uid
            assert rec[5] == req
            return uid
        except RuntimeError:
            assert expected_err
            return multiple()

    @rule(uid=st.integers(min_value=1, max_value=8))
    def r_delete_answer(self, uid):
        """Test delete_answer method over RPC."""
        expected_err = False
        try:
            self.model.delete_answer(uid)
        except (ValueError, KeyError):
            expected_err = True
        try:
            res = self.client.delete_answer(uid)
            assert not expected_err
            assert res is True
        except RuntimeError:
            assert expected_err

    @rule()
    def r_get_all_answers(self):
        """Test get_all_answers method over RPC."""
        expected = sorted(self.model.get_all_answers())
        actual = sorted(self.client.get_all_answers())
        assert actual == expected

    @rule(
        uid=st.integers(min_value=1, max_value=8),
        ts=st.one_of(st.none(), st.integers(min_value=1000, max_value=2000)),
        out=st.one_of(st.none(), st.sampled_from(["new_1", "new_2"])),
        exc=st.one_of(st.none(), st.sampled_from(["None", "Err"])),
        req=st.one_of(st.none(), st.integers(min_value=1, max_value=8)),
        hit=st.one_of(st.none(), st.integers(min_value=0, max_value=1))
    )
    def r_update_answer(self, uid, ts, out, exc, req, hit):
        """Test update_answer method over RPC."""
        expected_err = False
        try:
            self.model.update_answer(
                uid, timestamp=ts, output=out, exception=exc,
                request=req, cache_hit=hit
            )
        except (ValueError, KeyError):
            expected_err = True
        try:
            rec = self.client.update_answer(
                uid, timestamp=ts, output=out, exception=exc,
                request=req, cache_hit=hit
            )
            assert not expected_err
            if out is not None:
                assert rec[2] == out
        except RuntimeError:
            assert expected_err

    @rule(now=st.integers(min_value=1000, max_value=2500))
    def r_query_join(self, now):
        """Test relational algebra query over RPC."""
        expected = sorted(self.model.query_sessions_requests(now))
        actual = sorted(self.client.query_sessions_requests(now=now))
        assert actual == expected


def test_rpc_model_based():
    """Execute hypothesis state machine comparing RPC against model."""
    run_state_machine_as_test(
        RPCModelComparison,
        settings=settings(
            max_examples=100,
            stateful_step_count=25,
            deadline=None
        )
    )
