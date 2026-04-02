from __future__ import annotations

import gzip
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from schem2mineclonia.mapping import MinecloniaMapper, MappedNode
from schem2mineclonia.mts import write_mts
from schem2mineclonia.sponge import load_schematic


TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


def _named_tag(tag_type: int, name: str, payload: bytes) -> bytes:
    encoded_name = name.encode("utf-8")
    return tag_type.to_bytes(1, "big") + struct.pack(">H", len(encoded_name)) + encoded_name + payload


def _tag_string(name: str, value: str) -> bytes:
    encoded = value.encode("utf-8")
    return _named_tag(TAG_STRING, name, struct.pack(">H", len(encoded)) + encoded)


def _tag_short(name: str, value: int) -> bytes:
    return _named_tag(TAG_SHORT, name, struct.pack(">h", value))


def _tag_int(name: str, value: int) -> bytes:
    return _named_tag(TAG_INT, name, struct.pack(">i", value))


def _tag_long(name: str, value: int) -> bytes:
    return _named_tag(TAG_LONG, name, struct.pack(">q", value))


def _tag_byte_array(name: str, value: bytes) -> bytes:
    return _named_tag(TAG_BYTE_ARRAY, name, struct.pack(">i", len(value)) + value)


def _tag_int_array(name: str, values: list[int]) -> bytes:
    payload = struct.pack(">i", len(values)) + b"".join(
        struct.pack(">i", value) for value in values
    )
    return _named_tag(TAG_INT_ARRAY, name, payload)


def _tag_long_array(name: str, values: list[int]) -> bytes:
    payload = struct.pack(">i", len(values)) + b"".join(
        struct.pack(">q", value) for value in values
    )
    return _named_tag(TAG_LONG_ARRAY, name, payload)


def _tag_list(name: str, element_type: int, payloads: list[bytes]) -> bytes:
    payload = bytes([element_type]) + struct.pack(">i", len(payloads)) + b"".join(payloads)
    return _named_tag(TAG_LIST, name, payload)


def _compound_payload(*entries: bytes) -> bytes:
    return b"".join(entries) + b"\x00"


def _tag_compound(name: str, payload: bytes) -> bytes:
    return _named_tag(TAG_COMPOUND, name, payload + b"\x00")


def _root_document(name: str, payload: bytes) -> bytes:
    encoded_name = name.encode("utf-8")
    return b"\x0a" + struct.pack(">H", len(encoded_name)) + encoded_name + payload


def _build_sponge_v2_schem(
    *,
    width: int,
    height: int,
    length: int,
    palette: dict[str, int],
    block_indices: list[int],
) -> bytes:
    palette_payload = b"".join(_tag_int(state, index) for state, index in palette.items())
    root_payload = _compound_payload(
        _tag_int("Version", 2),
        _tag_int("DataVersion", 3578),
        _tag_short("Width", width),
        _tag_short("Height", height),
        _tag_short("Length", length),
        _tag_int("PaletteMax", len(palette)),
        _tag_compound("Palette", palette_payload),
        _tag_byte_array("BlockData", bytes(block_indices)),
    )
    return gzip.compress(_root_document("Schematic", root_payload))


def _split_legacy_ids(block_ids: list[int]) -> tuple[bytes, bytes | None]:
    low = bytearray()
    high = bytearray((len(block_ids) + 1) // 2)
    needs_high = False

    for index, block_id in enumerate(block_ids):
        low.append(block_id & 0xFF)
        high_nibble = (block_id >> 8) & 0x0F
        if high_nibble:
            needs_high = True
        if index % 2 == 0:
            high[index // 2] |= high_nibble
        else:
            high[index // 2] |= high_nibble << 4

    return bytes(low), bytes(high) if needs_high else None


def _build_legacy_schematic(
    *,
    width: int,
    height: int,
    length: int,
    block_ids: list[int],
    data_values: list[int],
) -> bytes:
    blocks, add_blocks = _split_legacy_ids(block_ids)
    entries = [
        _tag_string("Materials", "Alpha"),
        _tag_short("Width", width),
        _tag_short("Height", height),
        _tag_short("Length", length),
        _tag_byte_array("Blocks", blocks),
        _tag_byte_array("Data", bytes(data_values)),
    ]
    if add_blocks is not None:
        entries.append(_tag_byte_array("AddBlocks", add_blocks))

    return gzip.compress(_root_document("Schematic", _compound_payload(*entries)))


def _pack_litematic_block_states(indices: list[int], palette_size: int) -> list[int]:
    bits = max((palette_size - 1).bit_length(), 2)
    total_longs = (len(indices) * bits + 63) // 64
    array = [0] * total_longs
    mask = (1 << bits) - 1
    full_mask = (1 << 64) - 1

    for index, value in enumerate(indices):
        start_offset = index * bits
        start_long = start_offset >> 6
        end_long = ((index + 1) * bits - 1) >> 6
        bit_offset = start_offset & 0x3F

        array[start_long] = (
            (array[start_long] & ~(mask << bit_offset)) | ((value & mask) << bit_offset)
        ) & full_mask
        if start_long != end_long:
            end_offset = 64 - bit_offset
            spill_bits = bits - end_offset
            array[end_long] = (
                (array[end_long] >> spill_bits << spill_bits)
                | ((value & mask) >> end_offset)
            ) & full_mask

    signed: list[int] = []
    sign_bit = 1 << 63
    for value in array:
        if value & sign_bit:
            signed.append(value - (1 << 64))
        else:
            signed.append(value)
    return signed


def _blockstate_payload(state: str) -> bytes:
    if "[" not in state:
        return _compound_payload(_tag_string("Name", state))

    name, raw_props = state[:-1].split("[", 1)
    props = []
    for item in raw_props.split(","):
        key, value = item.split("=", 1)
        props.append(_tag_string(key, value))
    return _compound_payload(
        _tag_string("Name", name),
        _tag_compound("Properties", b"".join(props)),
    )


def _litematic_region_payload(
    *,
    position: tuple[int, int, int],
    size: tuple[int, int, int],
    palette: list[str],
    block_indices: list[int],
) -> bytes:
    packed = _pack_litematic_block_states(block_indices, len(palette))
    return _compound_payload(
        _tag_compound(
            "Position",
            b"".join(
                (
                    _tag_int("x", position[0]),
                    _tag_int("y", position[1]),
                    _tag_int("z", position[2]),
                )
            ),
        ),
        _tag_compound(
            "Size",
            b"".join(
                (
                    _tag_int("x", size[0]),
                    _tag_int("y", size[1]),
                    _tag_int("z", size[2]),
                )
            ),
        ),
        _tag_list("BlockStatePalette", TAG_COMPOUND, [_blockstate_payload(state) for state in palette]),
        _tag_list("Entities", TAG_COMPOUND, []),
        _tag_list("TileEntities", TAG_COMPOUND, []),
        _tag_list("PendingBlockTicks", TAG_COMPOUND, []),
        _tag_list("PendingFluidTicks", TAG_COMPOUND, []),
        _tag_long_array("BlockStates", packed),
    )


def _build_litematic(regions: dict[str, bytes]) -> bytes:
    regions_payload = b"".join(
        _tag_compound(name, payload[:-1]) for name, payload in regions.items()
    )
    metadata_payload = b"".join(
        (
            _tag_string("Name", "fixture"),
            _tag_compound(
                "EnclosingSize",
                b"".join((_tag_int("x", 3), _tag_int("y", 1), _tag_int("z", 2))),
            ),
        )
    )
    root_payload = _compound_payload(
        _tag_int("Version", 6),
        _tag_int("SubVersion", 1),
        _tag_int("MinecraftDataVersion", 3578),
        _tag_compound("Metadata", metadata_payload),
        _tag_compound("Regions", regions_payload),
    )
    return gzip.compress(_root_document("", root_payload))


def _parse_mts(path: Path):
    data = path.read_bytes()
    width, height, length = struct.unpack(">3H", data[6:12])
    offset = 12 + height
    name_count = struct.unpack(">H", data[offset : offset + 2])[0]
    offset += 2

    names = []
    for _ in range(name_count):
        name_len = struct.unpack(">H", data[offset : offset + 2])[0]
        offset += 2
        names.append(data[offset : offset + name_len].decode("utf-8"))
        offset += name_len

    payload = zlib.decompress(data[offset:])
    size = width * height * length
    content_ids = [
        struct.unpack(">H", payload[i * 2 : i * 2 + 2])[0]
        for i in range(size)
    ]
    param1 = list(payload[2 * size : 3 * size])
    param2 = list(payload[3 * size : 4 * size])
    return width, height, length, names, content_ids, param1, param2


class MappingTests(unittest.TestCase):
    def test_mapper_handles_sample_palette_blocks(self) -> None:
        mapper = MinecloniaMapper()
        cases = {
            "minecraft:weathered_copper": MappedNode("mcl_copper:block_weathered"),
            "minecraft:beacon": MappedNode("mcl_beacons:beacon"),
            "minecraft:amethyst_block": MappedNode("mcl_amethyst:amethyst_block"),
            "minecraft:light_blue_terracotta": MappedNode(
                "mcl_colorblocks:hardened_clay_light_blue"
            ),
            "minecraft:light_blue_glazed_terracotta[facing=north]": MappedNode(
                "mcl_colorblocks:glazed_terracotta_light_blue",
                param2=0,
            ),
            "minecraft:snow_block": MappedNode("mcl_core:snowblock"),
            "minecraft:white_terracotta": MappedNode(
                "mcl_colorblocks:hardened_clay_white"
            ),
            "minecraft:cut_copper": MappedNode("mcl_copper:block_cut"),
            "minecraft:stripped_birch_wood[axis=x]": MappedNode(
                "mcl_trees:bark_stripped_birch",
                param2=12,
            ),
            "minecraft:end_stone": MappedNode("mcl_end:end_stone"),
            "minecraft:white_concrete": MappedNode("mcl_colorblocks:concrete_white"),
            "minecraft:pink_wool": MappedNode("mcl_wool:pink"),
            "minecraft:blackstone": MappedNode("mcl_blackstone:blackstone"),
            "minecraft:nether_wart_block": MappedNode("mcl_nether:nether_wart_block"),
            "minecraft:oak_stairs[facing=west,half=top,shape=straight]": MappedNode(
                "mcl_stairs:stair_oak",
                param2=21,
            ),
            "minecraft:dark_oak_slab[type=double]": MappedNode(
                "mcl_stairs:slab_dark_oak_double"
            ),
            "minecraft:light_blue_carpet": MappedNode("mcl_wool:light_blue_carpet"),
        }

        for raw_state, expected in cases.items():
            with self.subTest(raw_state=raw_state):
                self.assertEqual(mapper.map_blockstate(raw_state), expected)


class SpongeToMtsTests(unittest.TestCase):
    def test_v2_sponge_to_mts_round_trip(self) -> None:
        palette = {
            "minecraft:air": 0,
            "minecraft:stone": 1,
            "minecraft:light_blue_glazed_terracotta[facing=east]": 2,
            "minecraft:structure_void": 3,
        }
        block_indices = [1, 2, 3, 0]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "tiny.schem"
            output_path = Path(tmpdir) / "tiny.mts"
            input_path.write_bytes(
                _build_sponge_v2_schem(
                    width=2,
                    height=1,
                    length=2,
                    palette=palette,
                    block_indices=block_indices,
                )
            )

            schematic = load_schematic(input_path)
            mapper = MinecloniaMapper()
            mapped_palette, _report = mapper.map_palette(
                schematic.palette,
                schematic.block_indices,
                block_entities_ignored=schematic.block_entities_count,
                entities_ignored=schematic.entities_count,
            )

            write_mts(
                output_path,
                width=schematic.width,
                height=schematic.height,
                length=schematic.length,
                block_indices=schematic.block_indices,
                mapped_palette=mapped_palette,
            )

            width, height, length, names, content_ids, param1, param2 = _parse_mts(
                output_path
            )

            self.assertEqual((width, height, length), (2, 1, 2))
            self.assertIn("air", names)
            self.assertIn("mcl_core:stone", names)
            self.assertIn("mcl_colorblocks:glazed_terracotta_light_blue", names)

            resolved_names = [names[index] for index in content_ids]
            self.assertEqual(
                resolved_names,
                [
                    "air",
                    "air",
                    "mcl_core:stone",
                    "mcl_colorblocks:glazed_terracotta_light_blue",
                ],
            )
            self.assertEqual(param1, [0, 127, 127, 127])
            self.assertEqual(param2[-1], 1)


class AdditionalFormatTests(unittest.TestCase):
    def test_legacy_schematic_to_mts_round_trip(self) -> None:
        block_ids = [1, 17, 238, 171]
        data_values = [0, 4, 1, 3]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "tiny.schematic"
            output_path = Path(tmpdir) / "tiny.mts"
            input_path.write_bytes(
                _build_legacy_schematic(
                    width=2,
                    height=1,
                    length=2,
                    block_ids=block_ids,
                    data_values=data_values,
                )
            )

            schematic = load_schematic(input_path)
            mapper = MinecloniaMapper()
            mapped_palette, _report = mapper.map_palette(
                schematic.palette,
                schematic.block_indices,
                block_entities_ignored=schematic.block_entities_count,
                entities_ignored=schematic.entities_count,
            )
            write_mts(
                output_path,
                width=schematic.width,
                height=schematic.height,
                length=schematic.length,
                block_indices=schematic.block_indices,
                mapped_palette=mapped_palette,
            )

            width, height, length, names, content_ids, _param1, param2 = _parse_mts(
                output_path
            )

            self.assertEqual((width, height, length), (2, 1, 2))
            resolved_names = [names[index] for index in content_ids]
            self.assertEqual(
                resolved_names,
                [
                    "mcl_colorblocks:glazed_terracotta_light_blue",
                    "mcl_wool:light_blue_carpet",
                    "mcl_core:stone",
                    "mcl_trees:tree_oak",
                ],
            )
            self.assertEqual(param2, [3, 0, 0, 12])

    def test_litematic_to_mts_round_trip(self) -> None:
        region_a = _litematic_region_payload(
            position=(2, 0, 0),
            size=(1, 1, 1),
            palette=["minecraft:air", "minecraft:stone"],
            block_indices=[1],
        )
        region_b = _litematic_region_payload(
            position=(1, 0, 1),
            size=(-2, 1, 1),
            palette=[
                "minecraft:air",
                "minecraft:oak_log[axis=x]",
                "minecraft:light_blue_glazed_terracotta[facing=south]",
            ],
            block_indices=[1, 2],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "tiny.litematic"
            output_path = Path(tmpdir) / "tiny.mts"
            input_path.write_bytes(
                _build_litematic(
                    {
                        "stone": region_a,
                        "details": region_b,
                    }
                )
            )

            schematic = load_schematic(input_path)
            mapper = MinecloniaMapper()
            mapped_palette, _report = mapper.map_palette(
                schematic.palette,
                schematic.block_indices,
                block_entities_ignored=schematic.block_entities_count,
                entities_ignored=schematic.entities_count,
            )
            write_mts(
                output_path,
                width=schematic.width,
                height=schematic.height,
                length=schematic.length,
                block_indices=schematic.block_indices,
                mapped_palette=mapped_palette,
            )

            width, height, length, names, content_ids, _param1, param2 = _parse_mts(
                output_path
            )

            self.assertEqual((width, height, length), (3, 1, 2))
            resolved_names = [names[index] for index in content_ids]
            self.assertEqual(
                resolved_names,
                [
                    "mcl_trees:tree_oak",
                    "mcl_colorblocks:glazed_terracotta_light_blue",
                    "air",
                    "air",
                    "air",
                    "mcl_core:stone",
                ],
            )
            self.assertEqual(param2, [12, 2, 0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
