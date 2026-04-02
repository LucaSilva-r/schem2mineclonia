"""Load Litematic `.litematic` files."""

from __future__ import annotations

from math import ceil
from typing import Any

from .model import MinecraftSchematic
from .nbt import NBTError


def load_litematic(root: dict[str, Any]) -> MinecraftSchematic:
    regions = root.get("Regions")
    if not isinstance(regions, dict) or not regions:
        raise NBTError("Litematic file is missing the Regions compound")

    bounds = [_region_bounds(region) for region in regions.values()]
    min_x = min(bound[0] for bound in bounds)
    min_y = min(bound[1] for bound in bounds)
    min_z = min(bound[2] for bound in bounds)
    max_x = max(bound[3] for bound in bounds)
    max_y = max(bound[4] for bound in bounds)
    max_z = max(bound[5] for bound in bounds)

    width = max_x - min_x + 1
    height = max_y - min_y + 1
    length = max_z - min_z + 1

    palette = ["minecraft:air"]
    palette_lookup = {"minecraft:air": 0}
    block_indices = [0] * (width * height * length)
    block_entities_count = 0
    entities_count = 0

    for region in regions.values():
        size = region.get("Size")
        position = region.get("Position")
        if not isinstance(size, dict) or not isinstance(position, dict):
            raise NBTError("Litematic region is missing Position or Size")

        size_x = int(size["x"])
        size_y = int(size["y"])
        size_z = int(size["z"])
        pos_x = int(position["x"])
        pos_y = int(position["y"])
        pos_z = int(position["z"])
        volume = abs(size_x * size_y * size_z)
        if volume <= 0:
            raise NBTError("Litematic region dimensions must be non-zero")

        region_palette = _region_palette(region)
        region_indices = _decode_packed_indices(
            region.get("BlockStates"),
            volume,
            len(region_palette),
        )

        for linear_index, palette_index in enumerate(region_indices):
            if palette_index < 0 or palette_index >= len(region_palette):
                raise NBTError(
                    "Litematic block palette index is out of bounds for the region palette"
                )

            state = region_palette[palette_index]
            global_palette_index = palette_lookup.get(state)
            if global_palette_index is None:
                global_palette_index = len(palette)
                palette_lookup[state] = global_palette_index
                palette.append(state)

            y = linear_index // (abs(size_x) * abs(size_z))
            in_layer = linear_index % (abs(size_x) * abs(size_z))
            z = in_layer // abs(size_x)
            x = in_layer % abs(size_x)

            local_x = _store_to_local(x, size_x)
            local_y = _store_to_local(y, size_y)
            local_z = _store_to_local(z, size_z)

            absolute_x = pos_x + local_x
            absolute_y = pos_y + local_y
            absolute_z = pos_z + local_z
            target = _linear_index(
                absolute_x - min_x,
                absolute_y - min_y,
                absolute_z - min_z,
                width,
                length,
            )
            block_indices[target] = global_palette_index

        block_entities = region.get("TileEntities", [])
        if isinstance(block_entities, list):
            block_entities_count += len(block_entities)
        entities = region.get("Entities", [])
        if isinstance(entities, list):
            entities_count += len(entities)

    return MinecraftSchematic(
        width=width,
        height=height,
        length=length,
        palette=palette,
        block_indices=block_indices,
        version=int(root.get("Version", 0)),
        data_version=int(root["MinecraftDataVersion"])
        if "MinecraftDataVersion" in root
        else None,
        block_entities_count=block_entities_count,
        entities_count=entities_count,
        offset=(min_x, min_y, min_z),
    )


def _region_bounds(region: dict[str, Any]) -> tuple[int, int, int, int, int, int]:
    size = region.get("Size")
    position = region.get("Position")
    if not isinstance(size, dict) or not isinstance(position, dict):
        raise NBTError("Litematic region is missing Position or Size")

    pos_x = int(position["x"])
    pos_y = int(position["y"])
    pos_z = int(position["z"])
    size_x = int(size["x"])
    size_y = int(size["y"])
    size_z = int(size["z"])
    if size_x == 0 or size_y == 0 or size_z == 0:
        raise NBTError("Litematic region dimensions must be non-zero")

    end_x = pos_x + size_x - 1 if size_x > 0 else pos_x + size_x + 1
    end_y = pos_y + size_y - 1 if size_y > 0 else pos_y + size_y + 1
    end_z = pos_z + size_z - 1 if size_z > 0 else pos_z + size_z + 1
    return (
        min(pos_x, end_x),
        min(pos_y, end_y),
        min(pos_z, end_z),
        max(pos_x, end_x),
        max(pos_y, end_y),
        max(pos_z, end_z),
    )


def _region_palette(region: dict[str, Any]) -> list[str]:
    palette_tag = region.get("BlockStatePalette")
    if not isinstance(palette_tag, list) or not palette_tag:
        raise NBTError("Litematic region is missing a block palette")
    return [_blockstate_identifier_from_compound(entry) for entry in palette_tag]


def _blockstate_identifier_from_compound(entry: Any) -> str:
    if not isinstance(entry, dict) or "Name" not in entry:
        raise NBTError("Litematic palette entry is missing the Name tag")

    block_name = str(entry["Name"])
    properties = entry.get("Properties")
    if not isinstance(properties, dict) or not properties:
        return block_name

    serialized = ",".join(
        f"{key}={properties[key]}" for key in sorted(properties.keys())
    )
    return f"{block_name}[{serialized}]"


def _decode_packed_indices(
    raw_longs: Any,
    expected_count: int,
    palette_size: int,
) -> list[int]:
    if not isinstance(raw_longs, list):
        raise NBTError("Litematic region is missing the BlockStates long array")
    if palette_size <= 0:
        raise NBTError("Litematic region palette is empty")

    bits = max((palette_size - 1).bit_length(), 2)
    expected_longs = ceil(expected_count * bits / 64)
    if len(raw_longs) != expected_longs:
        raise NBTError(
            "Litematic BlockStates array length does not match the region volume"
        )

    mask = (1 << bits) - 1
    values = [int(value) & ((1 << 64) - 1) for value in raw_longs]
    out: list[int] = []
    for index in range(expected_count):
        start = index * bits
        start_long = start >> 6
        end_long = ((index + 1) * bits - 1) >> 6
        bit_offset = start & 0x3F
        if start_long == end_long:
            value = (values[start_long] >> bit_offset) & mask
        else:
            end_offset = 64 - bit_offset
            value = (
                (values[start_long] >> bit_offset)
                | (values[end_long] << end_offset)
            ) & mask
        out.append(value)
    return out


def _store_to_local(index: int, size: int) -> int:
    if size < 0:
        return index + size + 1
    return index


def _linear_index(x: int, y: int, z: int, width: int, length: int) -> int:
    return y * width * length + z * width + x
