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


def _tag_string(name: str, value: str) -> bytes:
    encoded_name = name.encode("utf-8")
    encoded_value = value.encode("utf-8")
    return (
        b"\x08"
        + struct.pack(">H", len(encoded_name))
        + encoded_name
        + struct.pack(">H", len(encoded_value))
        + encoded_value
    )


def _tag_short(name: str, value: int) -> bytes:
    encoded_name = name.encode("utf-8")
    return b"\x02" + struct.pack(">H", len(encoded_name)) + encoded_name + struct.pack(">h", value)


def _tag_int(name: str, value: int) -> bytes:
    encoded_name = name.encode("utf-8")
    return b"\x03" + struct.pack(">H", len(encoded_name)) + encoded_name + struct.pack(">i", value)


def _tag_byte_array(name: str, value: bytes) -> bytes:
    encoded_name = name.encode("utf-8")
    return (
        b"\x07"
        + struct.pack(">H", len(encoded_name))
        + encoded_name
        + struct.pack(">i", len(value))
        + value
    )


def _tag_compound(name: str, payload: bytes) -> bytes:
    encoded_name = name.encode("utf-8")
    return b"\x0a" + struct.pack(">H", len(encoded_name)) + encoded_name + payload + b"\x00"


def _build_sponge_v2_schem(
    *,
    width: int,
    height: int,
    length: int,
    palette: dict[str, int],
    block_indices: list[int],
) -> bytes:
    palette_payload = b"".join(_tag_int(state, index) for state, index in palette.items())
    root = bytearray()
    root.extend(b"\x0a")
    root.extend(struct.pack(">H", len("Schematic")))
    root.extend(b"Schematic")
    root.extend(_tag_int("Version", 2))
    root.extend(_tag_int("DataVersion", 3578))
    root.extend(_tag_short("Width", width))
    root.extend(_tag_short("Height", height))
    root.extend(_tag_short("Length", length))
    root.extend(_tag_int("PaletteMax", len(palette)))
    root.extend(_tag_compound("Palette", palette_payload))
    root.extend(_tag_byte_array("BlockData", bytes(block_indices)))
    root.extend(b"\x00")
    return gzip.compress(bytes(root))


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


if __name__ == "__main__":
    unittest.main()
