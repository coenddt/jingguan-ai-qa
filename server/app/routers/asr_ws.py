"""语音输入 → 豆包语音识别 2.0 中间 WebSocket 路由（前端双向流式）

前端以原生 WebSocket 连本端点（同源握手自动带登录 Cookie）：
- 首帧文本 {action:'start'} → 建火山会话；
- 后续二进制 → PCM 音频，以 SendAudio 帧转发火山；
- 文本 {action:'end'} → 发 FinishSession；
- 火山识别文本经同一连接以文本帧实时下行 {type:'transcript',text,final}，结束发 {type:'done'}，失败发 {type:'error',detail}。
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth.service import verify_token
from app.services import asr_service

router = APIRouter(prefix='/api', tags=['asr'])
logger = logging.getLogger(__name__)

_DISCONNECT_CODE = 4401  # 未登录
_BAD_REQ_CODE = 4400  # 首帧非法


def _extract_token(websocket: WebSocket) -> str:
    """从握手 Cookie 解析登录令牌 jg_token（返回空串即未登录）。"""
    cookie = websocket.headers.get('cookie', '')
    for part in cookie.split(';'):
        part = part.strip()
        if part.startswith('jg_token='):
            return part[len('jg_token='):].strip('"')
    return ''


async def _read_start(websocket: WebSocket) -> tuple[dict | None, int | None]:
    """读取并校验首帧 {action:'start'}。返回 (first, close_code)。

    - 前端断开：无 close_code（正常结束，不主动 close）。
    - 首帧非法（超时/非 JSON/非 start）：close_code=4400（bad request）。
    调用方 first 为 None 时按 close_code 决定是否 close 后返回。
    """
    try:
        raw = await websocket.receive_text()
    except WebSocketDisconnect:
        return None, None
    except Exception:
        return None, _BAD_REQ_CODE
    try:
        first = json.loads(raw)
    except ValueError:
        return None, _BAD_REQ_CODE
    if not isinstance(first, dict) or first.get('action') != 'start':
        return None, _BAD_REQ_CODE
    return first, None


async def _forward_to_frontend(websocket: WebSocket, incoming: asyncio.Queue) -> None:
    """消费火山识别结果队列，下行给前端；读到 done 哨兵后结束。"""
    while True:
        item = await incoming.get()
        kind = item.get('type')
        if kind == 'text':
            await websocket.send_text(json.dumps({
                'type': 'transcript',
                'text': item['text'],
                'final': item.get('final', False),
            }, ensure_ascii=False))
        elif kind == 'error':
            await websocket.send_text(
                json.dumps({'type': 'error', 'detail': item['detail']}, ensure_ascii=False))
        elif kind == 'done':
            await websocket.send_text(json.dumps({'type': 'done'}))
            return


async def _recv_frontend(websocket: WebSocket, session: 'asr_service.AsrSession') -> None:
    """循环接收前端帧：二进制→转发音频，文本控制→end 时 finish；断开即结束。"""
    while True:
        msg = await websocket.receive()
        if msg.get('type') == 'websocket.disconnect':
            return
        if msg.get('bytes'):
            data = msg['bytes']
            if data:
                try:
                    await session.send_audio(data)
                except Exception:
                    return
        elif msg.get('text'):
            try:
                ctrl = json.loads(msg['text'])
            except ValueError:
                continue
            if ctrl.get('action') == 'end':
                try:
                    await session.finish()
                except Exception:
                    return


@router.websocket('/asr/ws')
async def asr_ws(websocket: WebSocket):
    """语音流式中继端点：鉴权 → 首帧 start → 建火山会话 → 音频转发/结果下行 → end 收尾。"""
    token = _extract_token(websocket)
    if not verify_token(token):
        await websocket.close(code=_DISCONNECT_CODE)
        return
    await websocket.accept()

    session = None
    recv_task = None
    sink_task = None
    try:
        # 首帧强制 start（非法/断开由 _read_start 归一为 None + close_code）
        first, close_code = await _read_start(websocket)
        if first is None:
            if close_code is not None:
                await websocket.close(code=close_code)
            return

        incoming: asyncio.Queue = asyncio.Queue()
        try:
            session = await asr_service.AsrSession.open(incoming)
        except asr_service.AsrSessionError as e:
            # 建联失败/未配置：将病灶反馈下行，避免前端静默（自动反馈原则）
            await websocket.send_text(
                json.dumps({'type': 'error', 'detail': str(e)}, ensure_ascii=False))
            await websocket.close()
            return

        recv_task = asyncio.create_task(_recv_frontend(websocket, session))
        sink_task = asyncio.create_task(_forward_to_frontend(websocket, incoming))
        await asyncio.wait({recv_task, sink_task}, return_when=asyncio.FIRST_COMPLETED)
    except Exception as e:  # 兜底：任何异常都不静默，下行错误并记录
        logger.warning('asr.ws.error: %s', e)
        try:
            await websocket.send_text(
                json.dumps({'type': 'error', 'detail': str(e)}, ensure_ascii=False))
        except Exception:
            pass
    finally:
        for t in (recv_task, sink_task):
            if t and not t.done():
                t.cancel()
        for t in (recv_task, sink_task):
            if t:
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
        if session:
            await session.close()
