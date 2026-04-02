"""Write Luanti MTS v4 schematics."""

from __future__ import annotations

import struct
import zlib
from collections import OrderedDict
from pathlib import Path

from .mapping import MappedNode


def write_mts(
    path: str | Path,
    *,
    width: int,
    height: int,
    length: int,
    block_indices: list[int],
    mapped_palette: list[MappedNode],
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    name_ids: OrderedDict[str, int] = OrderedDict()
    for node in mapped_palette:
        if node.name not in name_ids:
            name_ids[node.name] = len(name_ids)

    content = bytearray()
    param1 = bytearray()
    param2 = bytearray()

    for z in range(length - 1, -1, -1):
        for y in range(height):
            for x in range(width):
                index = x + z * width + y * width * length
                node = mapped_palette[block_indices[index]]
                content.extend(struct.pack(">H", name_ids[node.name]))
                param1.append(node.param1)
                param2.append(node.param2)

    header = bytearray()
    header.extend(b"MTSM")
    header.extend(struct.pack(">H", 4))
    header.extend(struct.pack(">H", width))
    header.extend(struct.pack(">H", height))
    header.extend(struct.pack(">H", length))
    header.extend(bytes([127] * height))
    header.extend(struct.pack(">H", len(name_ids)))
    for name in name_ids:
        encoded = name.encode("utf-8")
        header.extend(struct.pack(">H", len(encoded)))
        header.extend(encoded)

    payload = zlib.compress(bytes(content + param1 + param2), level=9)
    path.write_bytes(bytes(header) + payload)
