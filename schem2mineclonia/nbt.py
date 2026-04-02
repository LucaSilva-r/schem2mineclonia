"""Minimal NBT reader for Sponge schematics."""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass
from typing import Any


TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


class NBTError(ValueError):
    """Raised when an NBT payload is malformed or unsupported."""


@dataclass(frozen=True)
class NBTDocument:
    """Top-level parsed NBT document."""

    name: str
    root: dict[str, Any]


def read_nbt_document(data: bytes) -> NBTDocument:
    stream = io.BytesIO(data)
    tag_type = _read_u8(stream)
    if tag_type != TAG_COMPOUND:
        raise NBTError(f"Expected a compound root tag, got tag type {tag_type}")
    name = _read_string(stream)
    root = _read_payload(stream, TAG_COMPOUND)
    if stream.read(1):
        raise NBTError("Trailing bytes found after root compound")
    return NBTDocument(name=name, root=root)


def decode_varints(data: bytes, expected_count: int) -> list[int]:
    """Decode a byte array of unsigned varints."""

    values: list[int] = []
    index = 0

    while index < len(data) and len(values) < expected_count:
        shift = 0
        value = 0
        while True:
            if index >= len(data):
                raise NBTError("Unexpected end of varint data")
            byte = data[index]
            index += 1
            value |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
            if shift >= 35:
                raise NBTError("Varint is too large")
        values.append(value)

    if len(values) != expected_count:
        raise NBTError(
            f"Decoded {len(values)} varints, expected {expected_count}"
        )
    if index != len(data):
        raise NBTError("Extra bytes found after decoding all expected varints")

    return values


def _read_payload(stream: io.BytesIO, tag_type: int) -> Any:
    if tag_type == TAG_END:
        return None
    if tag_type == TAG_BYTE:
        return _read_s8(stream)
    if tag_type == TAG_SHORT:
        return _read_s16(stream)
    if tag_type == TAG_INT:
        return _read_s32(stream)
    if tag_type == TAG_LONG:
        return _read_s64(stream)
    if tag_type == TAG_FLOAT:
        return _read_exact(stream, 4, ">f")[0]
    if tag_type == TAG_DOUBLE:
        return _read_exact(stream, 8, ">d")[0]
    if tag_type == TAG_BYTE_ARRAY:
        length = _read_s32(stream)
        if length < 0:
            raise NBTError("Negative byte array length")
        return stream.read(length)
    if tag_type == TAG_STRING:
        return _read_string(stream)
    if tag_type == TAG_LIST:
        element_type = _read_u8(stream)
        length = _read_s32(stream)
        if length < 0:
            raise NBTError("Negative list length")
        return [_read_payload(stream, element_type) for _ in range(length)]
    if tag_type == TAG_COMPOUND:
        out: dict[str, Any] = {}
        while True:
            inner_type = _read_u8(stream)
            if inner_type == TAG_END:
                return out
            name = _read_string(stream)
            out[name] = _read_payload(stream, inner_type)
    if tag_type == TAG_INT_ARRAY:
        length = _read_s32(stream)
        if length < 0:
            raise NBTError("Negative int array length")
        return list(struct.unpack(f">{length}i", _read_exact_bytes(stream, 4 * length)))
    if tag_type == TAG_LONG_ARRAY:
        length = _read_s32(stream)
        if length < 0:
            raise NBTError("Negative long array length")
        return list(struct.unpack(f">{length}q", _read_exact_bytes(stream, 8 * length)))
    raise NBTError(f"Unsupported NBT tag type: {tag_type}")


def _read_string(stream: io.BytesIO) -> str:
    length = _read_u16(stream)
    raw = _read_exact_bytes(stream, length)
    return raw.decode("utf-8")


def _read_exact(stream: io.BytesIO, size: int, fmt: str) -> tuple[Any, ...]:
    raw = _read_exact_bytes(stream, size)
    return struct.unpack(fmt, raw)


def _read_exact_bytes(stream: io.BytesIO, size: int) -> bytes:
    raw = stream.read(size)
    if len(raw) != size:
        raise NBTError("Unexpected end of NBT stream")
    return raw


def _read_u8(stream: io.BytesIO) -> int:
    return _read_exact(stream, 1, ">B")[0]


def _read_s8(stream: io.BytesIO) -> int:
    return _read_exact(stream, 1, ">b")[0]


def _read_u16(stream: io.BytesIO) -> int:
    return _read_exact(stream, 2, ">H")[0]


def _read_s16(stream: io.BytesIO) -> int:
    return _read_exact(stream, 2, ">h")[0]


def _read_s32(stream: io.BytesIO) -> int:
    return _read_exact(stream, 4, ">i")[0]


def _read_s64(stream: io.BytesIO) -> int:
    return _read_exact(stream, 8, ">q")[0]
