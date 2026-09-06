"""豆包语音识别 2.0（bigmodel_async）WebSocket 二进制协议编解码

大模型流式 ASR 简化协议（无事件号，用 MessageType 区分不同帧）：
- 上行：Header(4B) + PayloadSize(4B) + Payload
  * type=1 full client request：首帧，Payload 为 JSON 配置。
  * type=2 audio only request：逐包音频，Payload 为原始音频（serial=raw）。
  * 结束：audio only request 带"最后一包"标志（flags=0b0010），Payload 可为空。
- 下行：Header(4B) + [Sequence(4B)] + PayloadSize(4B) + Payload
  * type=9 full server response：识别结果，Payload 为 JSON。
  * type=15 错误。
Header 4 字节：byte0=协议版本|头部长度(4字节单位)  byte1=消息类型|特定标志
              byte2=序列化方法|压缩类型                byte3=保留
全部整型均为大端。纯工具，无 IO、无依赖注入，便于单测。
"""

from __future__ import annotations

import json
import struct
import zlib
from dataclasses import dataclass

# 消息类型（byte1 高 4 位）
MT_FULL_CLIENT_REQUEST = 0b0001  # 1：首帧，携带 JSON 配置
MT_AUDIO_ONLY_REQUEST = 0b0010  # 2：音频帧
MT_FULL_SERVER_RESPONSE = 0b1001  # 9：识别结果（JSON）
MT_ERROR_RESPONSE = 0b1111  # 15：错误

# Message type specific flags（byte1 低 4 位）
# 0b0001 - header 后 4 字节为 sequence number 且为正
# 0b0010 - header 后不含 sequence，仅指示此为最后一包（负包）
# 0b0011 - header 后 4 字节为 sequence number 且为负（最后一包）
_FLAG_HAS_SEQ = 0b0001
_FLAG_LAST_PACKET = 0b0010

_SERIAL_JSON = 0b0001
_SERIAL_RAW = 0b0000
_COMPRESS_NONE = 0b0000
_COMPRESS_GZIP = 0b0001


@dataclass
class ParsedFrame:
    """解析后的下行帧。payload 已按声明的压缩方式解压为原始字节。"""

    message_type: int
    sequence: int | None  # 下行若带 sequence 则为 int，否则 None
    payload: bytes


def _header(message_type: int, flags: int, serial: int, compression: int) -> bytes:
    return bytes([
        0x11,  # 协议版本 0b0001 | 头部长度 0b0001（4 字节）
        (message_type << 4) | flags,
        (serial << 4) | compression,
        0x00,
    ])


def build_full_request(meta: dict) -> bytes:
    """构造首帧 full client request（type=1，JSON 配置，不压缩）。"""
    payload = json.dumps(meta, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    header = _header(MT_FULL_CLIENT_REQUEST, 0, _SERIAL_JSON, _COMPRESS_NONE)
    out = bytearray(header)
    out += struct.pack('>I', len(payload))
    out += payload
    return bytes(out)


def build_audio_frame(audio: bytes, is_last: bool = False) -> bytes:
    """构造音频帧 audio only request（type=2，raw，不压缩）。

    is_last=True 时打上"最后一包"标志（结束/负包），Payload 可为空。
    """
    flags = _FLAG_LAST_PACKET if is_last else 0
    header = _header(MT_AUDIO_ONLY_REQUEST, flags, _SERIAL_RAW, _COMPRESS_NONE)
    audio = audio or b''
    out = bytearray(header)
    out += struct.pack('>I', len(audio))
    out += audio
    return bytes(out)


def parse_frame(data: bytes) -> ParsedFrame | None:
    """解析一个下行帧；数据不足/头损坏时返回 None。"""
    if len(data) < 4:
        return None
    header_size = data[0] & 0x0F
    header_len = header_size * 4
    message_type = (data[1] >> 4) & 0x0F
    flags = data[1] & 0x0F
    compression = data[2] & 0x0F

    offset = header_len
    sequence = None
    if flags & _FLAG_HAS_SEQ:
        # Header + Sequence(4)
        if len(data) < offset + 4:
            return None
        sequence = struct.unpack('>i', data[offset:offset + 4])[0]
        offset += 4

    # Header + PayloadSize(4) + Payload
    if len(data) < offset + 4:
        return None
    payload_size = struct.unpack('>I', data[offset:offset + 4])[0]
    offset += 4
    payload = data[offset:offset + payload_size]

    if compression == _COMPRESS_GZIP:
        try:
            payload = zlib.decompress(payload)
        except zlib.error as exc:
            raise ValueError('帧 payload Gzip 解压失败') from exc

    return ParsedFrame(message_type=message_type, sequence=sequence, payload=payload)


def _texts(items: object) -> list[str]:
    """从结果项（dict 列表）中抽取非空 text，保证元素均为 str。"""
    if not isinstance(items, list):
        return []
    return [t for i in items if isinstance(i, dict)
            for t in [i.get('text')] if isinstance(t, str) and t]


def _any_definite(items: object) -> bool:
    """结果项中是否有 definite=true（定稿）。"""
    if not isinstance(items, list):
        return False
    return any(isinstance(i, dict) and i.get('definite') for i in items)


def _extract_object_result(res: dict, obj: dict) -> tuple[str | None, bool]:
    """schema A：bigmodel_async 的 result 为对象。text + utterances[].definite 判定稿。"""
    t = res.get('text')
    text = t if isinstance(t, str) and t else None
    utts = res.get('utterances')
    if isinstance(utts, list):
        is_final = _any_definite(utts)
        if text is None:  # 顶层无 text 时用 utterances 拼接兜底
            parts = _texts(utts)
            if parts:
                text = ''.join(parts)
    else:
        is_final = False
    return text, is_final


def extract_text(frame: ParsedFrame) -> tuple[str | None, bool]:
    """从识别结果帧抽取文本（保守版：不抛错）。

    返回 (text, is_final)。下行 FullServerResponse 的 payload 常见两种 schema：
    - bigmodel_async（现状）result 为对象：{"text":..., "utterances":[{"text":..,"definite":..}]}，
      定稿由任一 utterance.definite=true 判定；
    - 兼容旧 schema result 为数组：[{"text":...}]，result_type=full 时为确定句。
    解析失败返回 (None, False)。
    """
    if frame.message_type == MT_ERROR_RESPONSE:
        return (None, False)
    try:
        obj = json.loads(frame.payload.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return (None, False)
    if not isinstance(obj, dict):
        return (None, False)

    res = obj.get('result')
    if isinstance(res, dict):
        text, is_final = _extract_object_result(res, obj)
    elif isinstance(res, list):
        # schema B：result 为数组（兼容旧接口）
        texts = _texts(res)
        text = ''.join(texts) if texts else None
        is_final = _any_definite(res)
    else:
        text = None
        is_final = False

    # 顶层 text 兜底
    if text is None and isinstance(obj.get('text'), str):
        text = obj['text']
    # result_type=full（无逐句 definite 的旧语义）视为该句已确定
    if text and not is_final and obj.get('result_type') == 'full':
        is_final = True
    return (text, is_final)
