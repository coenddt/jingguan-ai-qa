"""ASR 网络边界单测（本地内存态，不连火山、不起常驻服务，不违反服务器测试铁律）

- asr_service：patch websockets.connect 返回 fake 连接，喂下行帧验证 _read_loop 解码/错误/收尾。
- asr_ws：用 FastAPI TestClient（ASGI 内存应用，进程内建/销毁）验证 /api/asr/ws 路由鉴权/start/下行。
"""

import asyncio
import json
import struct

import pytest
import websockets
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient

from app.routers import asr_ws
from app.services import asr_protocol as P
from app.services import asr_service


def _result_frame(payload: dict) -> bytes:
    """构造 type=9 下行结果帧（bigmodel_async schema），序列化 JSON 不压缩。"""
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    header = bytes([0x11, (P.MT_FULL_SERVER_RESPONSE << 4), 0x10, 0x00])
    return header + struct.pack('>I', len(body)) + body


def _error_frame(payload: dict) -> bytes:
    """构造 type=15 下行错误帧。"""
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    header = bytes([0x11, (P.MT_ERROR_RESPONSE << 4), 0x10, 0x00])
    return header + struct.pack('>I', len(body)) + body


class _FakeVolcConn:
    """模拟火山下行 websocket：按序喂帧、记录上行 send、close 置标志。"""

    def __init__(self, frames: list[bytes]) -> None:
        self._frames = list(frames)
        self.sent: list[bytes] = []
        self.closed = False

    def __aiter__(self):
        self._it = iter(self._frames)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration

    async def send(self, data: bytes) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self.closed = True


def _patch_connect(monkeypatch, conn):
    async def fake_connect(*_a, **_k):
        return conn
    monkeypatch.setattr(websockets, 'connect', fake_connect)


def _enable_key(monkeypatch):
    monkeypatch.setattr(asr_service.cfg, 'ASR_API_KEY', 'test-key')


# ---------- asr_service ----------

def test_asr_session_open_and_text_downstream(monkeypatch):
    """open 建联成功，read_loop 收到 bigmodel 结果帧 → 队列出 text(final=true)。"""
    _enable_key(monkeypatch)
    fr = _result_frame({'result': {'text': '你好，测试。',
                                   'utterances': [{'text': '你好，测试。', 'definite': True}]}})
    _patch_connect(monkeypatch, _FakeVolcConn([fr]))

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        item = await incoming.get()
        await session.close()
        return item

    assert asyncio.run(scenario()) == {'type': 'text', 'text': '你好，测试。', 'final': True}


def test_asr_session_open_sends_full_request_first(monkeypatch):
    """open 首帧须为 full client request（type=1），且头部拼了鉴权。"""
    _enable_key(monkeypatch)
    conn = _FakeVolcConn([])
    _patch_connect(monkeypatch, conn)

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        await session.close()
        assert len(conn.sent) >= 1
        f0 = P.parse_frame(conn.sent[0])
        return f0.message_type if f0 else None

    assert asyncio.run(scenario()) == P.MT_FULL_CLIENT_REQUEST


def test_asr_session_send_audio_uses_audio_frame(monkeypatch):
    """send_audio 上行帧须为 type=2 音频帧。"""
    _enable_key(monkeypatch)
    conn = _FakeVolcConn([])
    _patch_connect(monkeypatch, conn)

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        await session.send_audio(b'\x00\x01')
        f1 = P.parse_frame(conn.sent[-1])
        await session.close()
        return f1.message_type if f1 else None

    assert asyncio.run(scenario()) == P.MT_AUDIO_ONLY_REQUEST


def test_asr_session_finish_marks_last_packet(monkeypatch):
    """finish 帧须携带"最后一包"标志。"""
    _enable_key(monkeypatch)
    conn = _FakeVolcConn([])
    _patch_connect(monkeypatch, conn)

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        await session.finish()
        last = conn.sent[-1]
        await session.close()
        return (last[1] & 0x0F) & P._FLAG_LAST_PACKET

    assert asyncio.run(scenario()) != 0


def test_asr_session_error_frame_yields_error_and_done(monkeypatch):
    """错误帧(15)：_failure 置位；队列依次出 error 与 done。"""
    _enable_key(monkeypatch)
    _patch_connect(monkeypatch, _FakeVolcConn(
        [_error_frame({'code': 'Invalid.OssKey', 'message': '鉴权失败'})]))

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        first = await incoming.get()
        second = await incoming.get()
        await session.close()
        return first, second

    first, second = asyncio.run(scenario())
    assert first['type'] == 'error' and '鉴权失败' in first['detail']
    assert second == {'type': 'done'}


def test_asr_session_graceful_close_yields_done(monkeypatch):
    """火山正常关连接（无失败）：队列只出 done。"""
    _enable_key(monkeypatch)
    _patch_connect(monkeypatch, _FakeVolcConn([]))

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        item = await incoming.get()
        await session.close()
        return item

    assert asyncio.run(scenario()) == {'type': 'done'}


def test_asr_session_missing_api_key_raises(monkeypatch):
    """未配置 ASR_API_KEY → open 抛 AsrSessionError（不触网）。"""
    monkeypatch.setattr(asr_service.cfg, 'ASR_API_KEY', '')

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        return await asr_service.AsrSession.open(incoming)

    with pytest.raises(asr_service.AsrSessionError):
        asyncio.run(scenario())


def test_asr_session_connect_failure_raises(monkeypatch):
    """建联失败（HTTP 401 等）→ AsrSessionError，不静默。"""
    _enable_key(monkeypatch)

    async def boom(*_a, **_k):
        raise ConnectionError('401 Unauthorized')
    monkeypatch.setattr(websockets, 'connect', boom)

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        return await asr_service.AsrSession.open(incoming)

    with pytest.raises(asr_service.AsrSessionError):
        asyncio.run(scenario())


def test_asr_session_close_idempotent(monkeypatch):
    """close 幂等且关闭底层连接。"""
    _enable_key(monkeypatch)
    conn = _FakeVolcConn([])
    _patch_connect(monkeypatch, conn)

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        await session.close()
        await session.close()
        return conn.closed

    assert asyncio.run(scenario()) is True


# ---------- asr_ws ----------

def _make_client() -> TestClient:
    app = FastAPI()
    # 复用 asr 服务端回调，仅用于 try_flow 中 patch open
    app.include_router(asr_ws.router)
    return TestClient(app)


class _FakeSession:
    def __init__(self, incoming: asyncio.Queue):
        self.incoming = incoming

    async def send_audio(self, data: bytes) -> None:
        pass

    async def finish(self) -> None:
        pass

    async def close(self) -> None:
        pass


def test_ws_extract_token():
    """从握手 Cookie 解析 jg_token（纯函数覆盖）。"""
    assert asr_ws._extract_token(type('H', (), {'headers': {'cookie': 'x=1; jg_token="tok"'}})()) == 'tok'
    assert asr_ws._extract_token(type('H', (), {'headers': {'cookie': 'x=1'}})()) == ''


def test_ws_transcript_and_done_flow(monkeypatch):
    """start → 建会话 → 下行 transcript 与 done 全流程（fake open）。"""
    client = _make_client()
    monkeypatch.setattr(asr_ws, 'verify_token', lambda t: bool(t))

    async def fake_open(incoming: asyncio.Queue):
        await incoming.put({'type': 'text', 'text': '你好', 'final': True})
        await incoming.put({'type': 'done'})
        return _FakeSession(incoming)

    monkeypatch.setattr(asr_service.AsrSession, 'open', fake_open)

    with client.websocket_connect('/api/asr/ws', cookies={'jg_token': 'tok'}) as ws:
        ws.send_text(json.dumps({'action': 'start'}))
        m1 = ws.receive_json()
        m2 = ws.receive_json()
        assert m1 == {'type': 'transcript', 'text': '你好', 'final': True}
        assert m2 == {'type': 'done'}


def test_ws_unauth_closed(monkeypatch):
    """未鉴权（令牌无效）→ 握手被 close(4401)。"""
    client = _make_client()
    monkeypatch.setattr(asr_ws, 'verify_token', lambda t: False)
    with pytest.raises(WebSocketDisconnect) as ei, \
            client.websocket_connect('/api/asr/ws', cookies={'jg_token': 'bad'}) as ws:
        ws.receive_text()
    assert ei.value.code == 4401


def test_ws_open_failure_downstreams_error(monkeypatch):
    """火山建联失败 → 下行 error 帧并关闭，前端不静默（自动反馈原则）。"""
    client = _make_client()
    monkeypatch.setattr(asr_ws, 'verify_token', lambda t: bool(t))

    async def fail_open(incoming: asyncio.Queue):
        raise asr_service.AsrSessionError('连接火山语音识别失败')

    monkeypatch.setattr(asr_service.AsrSession, 'open', fail_open)

    with client.websocket_connect('/api/asr/ws', cookies={'jg_token': 'tok'}) as ws:
        ws.send_text(json.dumps({'action': 'start'}))
        m = ws.receive_json()
        assert m['type'] == 'error' and '语音识别' in m['detail']


class _FakeWs:
    """进程内 fake 前端 websocket：顺序给消息、记录下行。"""

    def __init__(self, msgs: list[dict]) -> None:
        self._msgs = list(msgs)
        self.sent_text: list[str] = []
        self.sent_bytes: list[bytes] = []

    async def receive(self):
        return self._msgs.pop(0) if self._msgs else {'type': 'websocket.disconnect'}

    async def send_text(self, t: str) -> None:
        self.sent_text.append(t)

    async def send_bytes(self, b: bytes) -> None:
        self.sent_bytes.append(b)


class _RecSys:
    """记录 send_audio / finish 调用的 fake 会话。"""

    def __init__(self) -> None:
        self.audios: list[bytes] = []
        self.finished = 0

    async def send_audio(self, data: bytes) -> None:
        self.audios.append(data)

    async def finish(self) -> None:
        self.finished += 1


def test_ws_recv_frontend_audio_and_end():
    """_recv_frontend：二进制转音频、文本 end 触发 finish、disconnect 返回。"""
    sys = _RecSys()
    ws = _FakeWs([
        {'type': 'websocket.receive', 'bytes': b'\x00\x01'},
        {'type': 'websocket.receive', 'text': json.dumps({'action': 'end'})},
        {'type': 'websocket.disconnect'},
    ])

    asyncio.run(asr_ws._recv_frontend(ws, sys))
    assert sys.audios == [b'\x00\x01']
    assert sys.finished == 1


def test_ws_forward_to_frontend_error_and_done():
    """_forward_to_frontend：text 下行 transcript、error 下行、done 哨兵结束。"""
    incoming: asyncio.Queue = asyncio.Queue()
    ws = _FakeWs([])

    async def scenario():
        await incoming.put({'type': 'text', 'text': '你好', 'final': True})
        await incoming.put({'type': 'error', 'detail': 'boom'})
        await incoming.put({'type': 'done'})
        await asr_ws._forward_to_frontend(ws, incoming)
        return ws.sent_text

    sent = asyncio.run(scenario())
    assert sent[0] == json.dumps({'type': 'transcript', 'text': '你好', 'final': True}, ensure_ascii=False)
    assert sent[1] == json.dumps({'type': 'error', 'detail': 'boom'}, ensure_ascii=False)
    assert sent[2] == json.dumps({'type': 'done'})


def test_ws_first_frame_not_start_closed(monkeypatch):
    """首帧非 start → 服务端 close(bad request)，客户端 receive 抛差断。"""
    client = _make_client()
    monkeypatch.setattr(asr_ws, 'verify_token', lambda t: bool(t))
    with pytest.raises(WebSocketDisconnect) as ei, \
            client.websocket_connect('/api/asr/ws', cookies={'jg_token': 'tok'}) as ws:
        ws.send_text(json.dumps({'action': 'nope'}))
        ws.receive_text()  # 触发读取，服务端已 close(4400)
    assert ei.value.code == 4400


# ---------- asr_service 补充分支 ----------

def test_asr_session_send_config_failure_raises(monkeypatch):
    """open 发送首帧配置失败 → AsrSessionError 且关闭底层连接。"""
    _enable_key(monkeypatch)

    class BoomConn(_FakeVolcConn):
        async def send(self, data: bytes) -> None:
            raise ConnectionError('broken pipe')

    conn = BoomConn([])
    _patch_connect(monkeypatch, conn)

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        return await asr_service.AsrSession.open(incoming)

    with pytest.raises(asr_service.AsrSessionError):
        asyncio.run(scenario())


def test_asr_session_send_audio_and_finish_after_close_noop(monkeypatch):
    """会话已关闭后 send_audio / finish 为静默 no-op。"""
    _enable_key(monkeypatch)
    conn = _FakeVolcConn([])
    _patch_connect(monkeypatch, conn)

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        await session.close()
        n = len(conn.sent)
        await session.send_audio(b'x')   # 已 closed → 不发送
        await session.finish()
        return len(conn.sent) == n

    assert asyncio.run(scenario()) is True


def test_asr_session_str_downstream_frame_handled(monkeypatch):
    """火山下行若误发文本帧 str：转为 bytes 后解析失败被吞咽，不崩溃、无假文本。"""
    _enable_key(monkeypatch)
    # 非协议二进制帧的文本 str：encode 后 parse_frame 返回 None → continue → 正常收 done
    _patch_connect(monkeypatch, _FakeVolcConn(['this-is-not-a-frame']))

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        item = await incoming.get()
        await session.close()
        return item

    assert asyncio.run(scenario()) == {'type': 'done'}


def test_asr_session_decode_error_frame_json_fail(monkeypatch):
    """错误帧 payload 非 JSON → _decode_error 回退原文不抛错。"""
    _enable_key(monkeypatch)
    body = b'not-json'
    header = bytes([0x11, (P.MT_ERROR_RESPONSE << 4), 0x10, 0x00])
    bad = header + struct.pack('>I', len(body)) + body
    _patch_connect(monkeypatch, _FakeVolcConn([bad]))

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        first = await incoming.get()
        await session.close()
        return first

    first = asyncio.run(scenario())
    assert first['type'] == 'error' and 'not-json' in first['detail']


def test_asr_session_read_loop_interrupted_yields_error_done(monkeypatch):
    """下行迭代中途抛异常（连接中断）→ 出 error 与 done，不静默。"""
    _enable_key(monkeypatch)

    class InterruptConn(_FakeVolcConn):
        async def __anext__(self):
            raise ConnectionResetError('socket closed')

    _patch_connect(monkeypatch, InterruptConn([]))

    async def scenario():
        incoming: asyncio.Queue = asyncio.Queue()
        session = await asr_service.AsrSession.open(incoming)
        first = await incoming.get()
        second = await incoming.get()
        await session.close()
        return first, second

    first, second = asyncio.run(scenario())
    assert first['type'] == 'error' and '连接中断' in first['detail']
    assert second == {'type': 'done'}