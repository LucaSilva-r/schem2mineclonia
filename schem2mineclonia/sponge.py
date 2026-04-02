"""Load Minecraft schematic files into the shared palette model."""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Any

from .legacy import load_legacy_schematic
from .litematic import load_litematic
from .model import MinecraftSchematic, UnsupportedSchematicFormat
from .nbt import NBTDocument, NBTError, decode_varints, read_nbt_document


def load_schematic(path: str | Path) -> MinecraftSchematic:
    path = Path(path)
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)

    document = read_nbt_document(raw)
    root = _resolve_schematic_root(document)

    if _looks_like_litematic(root):
        return load_litematic(root)

    if "Materials" in root:
        return load_legacy_schematic(root)

    version = int(root.get("Version", 1))
    if version in {1, 2}:
        return _load_v1_v2(root, version)
    if version == 3:
        return _load_v3(root, version)

    raise UnsupportedSchematicFormat(
        f"Unsupported Sponge schematic version: {version}"
    )


def _looks_like_litematic(root: dict[str, Any]) -> bool:
    return isinstance(root.get("Regions"), dict) and isinstance(
        root.get("Metadata"), dict
    )


def _resolve_schematic_root(document: NBTDocument) -> dict[str, Any]:
    if document.name == "Schematic":
        return document.root
    if "Schematic" in document.root and isinstance(document.root["Schematic"], dict):
        return document.root["Schematic"]
    return document.root


def _load_v1_v2(root: dict[str, Any], version: int) -> MinecraftSchematic:
    width = int(root["Width"])
    height = int(root["Height"])
    length = int(root["Length"])
    palette = _invert_palette(root["Palette"])
    block_indices = decode_varints(root["BlockData"], width * height * length)
    _validate_palette_indices(block_indices, palette)

    block_entities = root.get("BlockEntities", [])
    entities = root.get("Entities", [])
    offset = tuple(root.get("Offset", [0, 0, 0]))
    if len(offset) != 3:
        offset = (0, 0, 0)

    return MinecraftSchematic(
        width=width,
        height=height,
        length=length,
        palette=palette,
        block_indices=block_indices,
        version=version,
        data_version=int(root["DataVersion"]) if "DataVersion" in root else None,
        block_entities_count=len(block_entities),
        entities_count=len(entities),
        offset=(int(offset[0]), int(offset[1]), int(offset[2])),
    )


def _load_v3(root: dict[str, Any], version: int) -> MinecraftSchematic:
    width = int(root["Width"])
    height = int(root["Height"])
    length = int(root["Length"])
    blocks = root.get("Blocks")
    if not isinstance(blocks, dict):
        raise NBTError("Sponge v3 schematic is missing the Blocks compound")

    palette_tag = blocks.get("Palette")
    if palette_tag is None:
        palette_tag = blocks.get("BlockPalette")
    if not isinstance(palette_tag, dict):
        raise NBTError("Sponge v3 schematic is missing a block palette")

    data_tag = blocks.get("Data")
    if data_tag is None:
        data_tag = blocks.get("BlockData")
    if not isinstance(data_tag, (bytes, bytearray)):
        raise NBTError("Sponge v3 schematic is missing block data")

    palette = _invert_palette(palette_tag)
    block_indices = decode_varints(bytes(data_tag), width * height * length)
    _validate_palette_indices(block_indices, palette)

    block_entities = blocks.get("BlockEntities", [])
    entities = root.get("Entities", [])
    offset = tuple(root.get("Offset", [0, 0, 0]))
    if len(offset) != 3:
        offset = (0, 0, 0)

    return MinecraftSchematic(
        width=width,
        height=height,
        length=length,
        palette=palette,
        block_indices=block_indices,
        version=version,
        data_version=int(root["DataVersion"]) if "DataVersion" in root else None,
        block_entities_count=len(block_entities),
        entities_count=len(entities),
        offset=(int(offset[0]), int(offset[1]), int(offset[2])),
    )


def _invert_palette(palette: dict[str, Any]) -> list[str]:
    if not palette:
        raise NBTError("Schematic palette is empty")

    max_index = max(int(index) for index in palette.values())
    out = [""] * (max_index + 1)
    for state, index in palette.items():
        out[int(index)] = state

    if any(not state for state in out):
        raise NBTError("Schematic palette contains holes")

    return out


def _validate_palette_indices(block_indices: list[int], palette: list[str]) -> None:
    max_index = len(palette) - 1
    for index in block_indices:
        if index < 0 or index > max_index:
            raise NBTError(
                f"Block palette index {index} is out of bounds for palette size {len(palette)}"
            )
