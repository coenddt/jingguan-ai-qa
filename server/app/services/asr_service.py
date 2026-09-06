"""豆包语音识别 2.0 双向流式会话（服务端连接火山 WebSocket 客户端）

工作方式：
- open()：连火山 bigmodel_async，发 full client request（JSON 配置），建会话。
- send_audio(data)：把前端音频 PCM 以 audio only request 帧上行转发。
- finish()：发"最后一包"（负包）帧，通知识别端本次音频结束。
- reader 解析下行帧：FullServerResponse(9) 抽取识别文本放入 incoming 队列，
  错误(Error=15)/连接关闭时放 done 哨兵。
- 调用方从 incoming 队列逐条消费 {'type':'text'|'done'|'error', ...}，并负责发送/收尾。
并发安全：音频/控制采用 asyncio.Lock 串行发送，满足 websockets 单写要求。
"""

import asyncio
import json
import logging
import uuid

import websockets

from app.config import ASR_AUDIO, ASR_REQUEST, ASR_RESOURCE_ID, ASR_WS_URL, cfg
from app.services import asr_protocol as P

logger = logging.getLogger(__name__)


class AsrSessionError(Exception):
    """火山侧建联/发送失败。message 面向自动反馈，供上层记录与下行给前端。"""


class AsrSession:
    """一个到火山的双向流式识别会话。"""

    def __init__(self, ws: websockets.ClientConnection, incoming: asyncio.Queue) -> None:
        self._ws = ws
        self._incoming = incoming
        self._write_lock = asyncio.Lock()
        self._failure: AsrSessionError | None = None
        self._reader: asyncio.Task | None = None
        self._closed = False

    @classmethod
    async def open(cls, incoming: asyncio.Queue) -> 'AsrSession':
        """建联并发起识别，收到配置后返回；建联/发送失败抛 AsrSessionError。"""
        if not cfg.ASR_API_KEY:
            raise AsrSessionError('语音识别未配置（ASR_API_KEY 缺失）')
        headers = {
            'X-Api-Key': cfg.ASR_API_KEY,
            'X-Api-Resource-Id': ASR_RESOURCE_ID,
            'X-Api-Request-Id': str(uuid.uuid4()),
            'X-Api-Sequence': '-1',
        }
        try:
            ws = await websockets.connect(ASR_WS_URL, additional_headers=headers)
        except Exception as e:  # 建 TCP/WS 失败（含 HTTP 401 等）
            raise AsrSessionError(f'连接火山语音识别失败: {e}') from e

        session = cls(ws, incoming)
        session._reader = asyncio.create_task(session._read_loop())
        try:
            await ws.send(P.build_full_request({'user': {'uid': cfg.ASR_API_KEY},
                                                'audio': ASR_AUDIO, 'request': ASR_REQUEST}))
        except Exception as e:
            await session.close()
            raise AsrSessionError(f'发送识别配置失败: {e}') from e
        return session

    async def send_audio(self, data: bytes) -> None:
        """上行转发一帧音频 PCM。会话已结束则静默忽略。"""
        async with self._write_lock:
            if self._closed or data is None or len(data) == 0:
                return
            await self._ws.send(P.build_audio_frame(data))

    async def finish(self) -> None:
        """发送"最后一包"结束帧，随后由 reader 到连接关闭后收帘。"""
        async with self._write_lock:
            if self._closed:
                return
            await self._ws.send(P.build_audio_frame(b'', is_last=True))

    async def close(self) -> None:
        """关闭火山连接并取消 reader。幂等。"""
        if self._closed:
            return
        self._closed = True
        if self._reader:
            self._reader.cancel()
            try:
                await self._reader
            except (asyncio.CancelledError, Exception):
                pass
            self._reader = None
        try:
            await self._ws.close()
        except Exception:
            pass

    def _decode_error(self, frame: P.ParsedFrame) -> AsrSessionError:
        text = frame.payload.decode('utf-8', 'ignore') or 'unknown'
        try:
            msg = json.loads(text)
            if isinstance(msg, dict):
                text = msg.get('message') or msg.get('code') or text
        except (ValueError, TypeError):
            pass
        return AsrSessionError(f'火山语音识别失败: {text}')

    async def _read_loop(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    if isinstance(raw, str):  # 火山下行恒为二进制；防文本帧误入
                        raw = raw.encode('utf-8')
                    frame = P.parse_frame(raw)
                except ValueError as e:
                    logger.warning('asr.frame_decode_failed: %s', e)
                    continue
                if frame is None:
                    continue

                if frame.message_type == P.MT_ERROR_RESPONSE:
                    self._failure = self._decode_error(frame)
                    break
                if frame.message_type == P.MT_FULL_SERVER_RESPONSE:
                    text, is_final = P.extract_text(frame)
                    if text:
                        self._incoming.put_nowait({'type': 'text', 'text': text, 'final': is_final})
        except asyncio.CancelledError:
            pass
        except Exception as e:  # 连接中断等
            self._failure = self._failure or AsrSessionError(f'火山识别连接中断: {e}')
        finally:
            if self._failure:
                self._incoming.put_nowait({'type': 'error', 'detail': str(self._failure)})
            self._incoming.put_nowait({'type': 'done'})
            self._closed = True
            try:
                await self._ws.close()
            except Exception:
                pass
