"""Load legacy MCEdit `.schematic` files."""

from __future__ import annotations

from typing import Any

from .model import MinecraftSchematic
from .nbt import NBTError


COLOR_NAMES = (
    "white",
    "orange",
    "magenta",
    "light_blue",
    "yellow",
    "lime",
    "pink",
    "gray",
    "light_gray",
    "cyan",
    "purple",
    "blue",
    "brown",
    "green",
    "red",
    "black",
)
WOOD_NAMES = ("oak", "spruce", "birch", "jungle", "acacia", "dark_oak")
STAIR_DIRECTIONS = {0: "east", 1: "west", 2: "south", 3: "north"}
HORIZONTAL_FACING = {0: "south", 1: "west", 2: "north", 3: "east"}
AXES = {0: "y", 1: "x", 2: "z"}


def load_legacy_schematic(root: dict[str, Any]) -> MinecraftSchematic:
    width = int(root["Width"])
    height = int(root["Height"])
    length = int(root["Length"])
    size = width * height * length

    blocks = root.get("Blocks")
    data = root.get("Data")
    if not isinstance(blocks, (bytes, bytearray)):
        raise NBTError("Legacy schematic is missing the Blocks byte array")
    if not isinstance(data, (bytes, bytearray)):
        raise NBTError("Legacy schematic is missing the Data byte array")
    if len(blocks) != size:
        raise NBTError(
            f"Legacy schematic has {len(blocks)} block IDs, expected {size}"
        )
    if len(data) != size:
        raise NBTError(
            f"Legacy schematic has {len(data)} block data entries, expected {size}"
        )

    add_blocks = root.get("AddBlocks")
    if add_blocks is None:
        add_blocks = root.get("Add")
    if add_blocks is not None and not isinstance(add_blocks, (bytes, bytearray)):
        raise NBTError("Legacy schematic AddBlocks tag must be a byte array")

    block_ids = _merge_block_ids(blocks, add_blocks)
    name_map = _resolve_legacy_name_map(root)

    palette_lookup: dict[str, int] = {}
    palette: list[str] = []
    block_indices: list[int] = []
    for index, block_id in enumerate(block_ids):
        state = legacy_block_to_state(block_id, data[index] & 0x0F, name_map.get(block_id))
        palette_index = palette_lookup.get(state)
        if palette_index is None:
            palette_index = len(palette)
            palette_lookup[state] = palette_index
            palette.append(state)
        block_indices.append(palette_index)

    tile_entities = root.get("TileEntities", [])
    if not isinstance(tile_entities, list):
        tile_entities = []
    entities = root.get("Entities", [])
    if not isinstance(entities, list):
        entities = []

    offset = (
        int(root.get("WEOffsetX", 0)),
        int(root.get("WEOffsetY", 0)),
        int(root.get("WEOffsetZ", 0)),
    )

    return MinecraftSchematic(
        width=width,
        height=height,
        length=length,
        palette=palette,
        block_indices=block_indices,
        version=0,
        data_version=int(root["DataVersion"]) if "DataVersion" in root else None,
        block_entities_count=len(tile_entities),
        entities_count=len(entities),
        offset=offset,
    )


def _merge_block_ids(
    blocks: bytes | bytearray,
    add_blocks: bytes | bytearray | None,
) -> list[int]:
    merged = [int(block_id) for block_id in blocks]
    if add_blocks is None:
        return merged

    expected_len = (len(blocks) + 1) // 2
    if len(add_blocks) != expected_len:
        raise NBTError(
            "Legacy schematic AddBlocks length does not match the Blocks array"
        )

    for index in range(len(merged)):
        extra = add_blocks[index // 2]
        high = extra & 0x0F if index % 2 == 0 else (extra >> 4) & 0x0F
        merged[index] |= high << 8
    return merged


def _resolve_legacy_name_map(root: dict[str, Any]) -> dict[int, str]:
    out: dict[int, str] = {}

    schematica_mapping = root.get("SchematicaMapping")
    if isinstance(schematica_mapping, dict):
        for name, raw_id in schematica_mapping.items():
            if isinstance(name, str):
                out[int(raw_id)] = name

    block_ids = root.get("BlockIDs")
    if isinstance(block_ids, dict):
        for raw_id, name in block_ids.items():
            if isinstance(name, str):
                out[int(raw_id)] = name

    return out


def legacy_block_to_state(block_id: int, data: int, name_hint: str | None = None) -> str:
    state = _legacy_block_to_state(block_id, data)
    if state is not None:
        return state
    if name_hint:
        return _unknown_named_state(name_hint, data)
    return f"legacy:id_{block_id}[data={data}]"


def _legacy_block_to_state(block_id: int, data: int) -> str | None:
    if block_id == 0:
        return "minecraft:air"
    if block_id == 1:
        return {
            0: "minecraft:stone",
            1: "minecraft:granite",
            2: "minecraft:polished_granite",
            3: "minecraft:diorite",
            4: "minecraft:polished_diorite",
            5: "minecraft:andesite",
            6: "minecraft:polished_andesite",
        }.get(data)
    if block_id == 2:
        return "minecraft:grass_block"
    if block_id == 3:
        return {
            0: "minecraft:dirt",
            1: "minecraft:coarse_dirt",
            2: "minecraft:podzol",
        }.get(data)
    if block_id == 4:
        return "minecraft:cobblestone"
    if block_id == 5 and data < len(WOOD_NAMES):
        return f"minecraft:{WOOD_NAMES[data]}_planks"
    if block_id == 6:
        variant = data & 0x07
        if variant < len(WOOD_NAMES):
            return f"minecraft:{WOOD_NAMES[variant]}_sapling"
        return None
    if block_id == 7:
        return "minecraft:bedrock"
    if block_id == 8:
        return "minecraft:water[level=1]"
    if block_id == 9:
        return "minecraft:water"
    if block_id == 10:
        return "minecraft:lava[level=1]"
    if block_id == 11:
        return "minecraft:lava"
    if block_id == 12:
        return "minecraft:sand" if data == 0 else "minecraft:red_sand" if data == 1 else None
    if block_id == 13:
        return "minecraft:gravel"
    if block_id == 14:
        return "minecraft:gold_ore"
    if block_id == 15:
        return "minecraft:iron_ore"
    if block_id == 16:
        return "minecraft:coal_ore"
    if block_id == 17:
        return _legacy_log_state(("oak", "spruce", "birch", "jungle"), data)
    if block_id == 18:
        return _legacy_leaves_state(("oak", "spruce", "birch", "jungle"), data)
    if block_id == 19:
        return "minecraft:sponge" if data == 0 else "minecraft:wet_sponge" if data == 1 else None
    if block_id == 20:
        return "minecraft:glass"
    if block_id == 21:
        return "minecraft:lapis_ore"
    if block_id == 22:
        return "minecraft:lapis_block"
    if block_id == 24:
        return {
            0: "minecraft:sandstone",
            1: "minecraft:chiseled_sandstone",
            2: "minecraft:smooth_sandstone",
        }.get(data)
    if block_id == 31:
        return {
            0: "minecraft:dead_bush",
            1: "minecraft:short_grass",
            2: "minecraft:fern",
        }.get(data)
    if block_id == 35 and data < len(COLOR_NAMES):
        return f"minecraft:{COLOR_NAMES[data]}_wool"
    if block_id == 41:
        return "minecraft:gold_block"
    if block_id == 42:
        return "minecraft:iron_block"
    if block_id == 43:
        return _legacy_stone_slab_state(data, doubled=True)
    if block_id == 44:
        return _legacy_stone_slab_state(data, doubled=False)
    if block_id == 45:
        return "minecraft:bricks"
    if block_id == 47:
        return "minecraft:bookshelf"
    if block_id == 48:
        return "minecraft:mossy_cobblestone"
    if block_id == 49:
        return "minecraft:obsidian"
    if block_id == 53:
        return _legacy_stair_state("oak", data)
    if block_id == 56:
        return "minecraft:diamond_ore"
    if block_id == 57:
        return "minecraft:diamond_block"
    if block_id == 58:
        return "minecraft:crafting_table"
    if block_id == 67:
        return _legacy_stair_state("cobblestone", data)
    if block_id in {73, 74}:
        return "minecraft:redstone_ore"
    if block_id == 79:
        return "minecraft:ice"
    if block_id == 80:
        return "minecraft:snow_block"
    if block_id == 82:
        return "minecraft:clay"
    if block_id == 84:
        return "minecraft:jukebox"
    if block_id == 87:
        return "minecraft:netherrack"
    if block_id == 88:
        return "minecraft:soul_sand"
    if block_id == 95 and data < len(COLOR_NAMES):
        return f"minecraft:{COLOR_NAMES[data]}_stained_glass"
    if block_id == 98:
        return {
            0: "minecraft:stone_bricks",
            1: "minecraft:mossy_stone_bricks",
            2: "minecraft:cracked_stone_bricks",
            3: "minecraft:chiseled_stone_bricks",
        }.get(data)
    if block_id == 108:
        return _legacy_stair_state("brick", data)
    if block_id == 109:
        return _legacy_stair_state("stone_brick", data)
    if block_id == 112:
        return "minecraft:nether_bricks"
    if block_id == 114:
        return _legacy_stair_state("nether_brick", data)
    if block_id == 121:
        return "minecraft:end_stone"
    if block_id == 125:
        return _legacy_wood_slab_state(data, doubled=True)
    if block_id == 126:
        return _legacy_wood_slab_state(data, doubled=False)
    if block_id == 128:
        return _legacy_stair_state("sandstone", data)
    if block_id == 129:
        return "minecraft:emerald_ore"
    if block_id == 133:
        return "minecraft:emerald_block"
    if block_id == 134:
        return _legacy_stair_state("spruce", data)
    if block_id == 135:
        return _legacy_stair_state("birch", data)
    if block_id == 136:
        return _legacy_stair_state("jungle", data)
    if block_id == 155:
        return {
            0: "minecraft:quartz_block",
            1: "minecraft:chiseled_quartz_block",
            2: "minecraft:quartz_pillar[axis=y]",
            3: "minecraft:quartz_pillar[axis=x]",
            4: "minecraft:quartz_pillar[axis=z]",
        }.get(data)
    if block_id == 156:
        return _legacy_stair_state("quartz", data)
    if block_id == 159 and data < len(COLOR_NAMES):
        return f"minecraft:{COLOR_NAMES[data]}_terracotta"
    if block_id == 162:
        return _legacy_log_state(("acacia", "dark_oak"), data)
    if block_id == 163:
        return _legacy_stair_state("acacia", data)
    if block_id == 164:
        return _legacy_stair_state("dark_oak", data)
    if block_id == 168:
        return {
            0: "minecraft:prismarine",
            1: "minecraft:prismarine_bricks",
            2: "minecraft:dark_prismarine",
        }.get(data)
    if block_id == 169:
        return "minecraft:sea_lantern"
    if block_id == 171 and data < len(COLOR_NAMES):
        return f"minecraft:{COLOR_NAMES[data]}_carpet"
    if block_id == 172:
        return "minecraft:terracotta"
    if block_id == 173:
        return "minecraft:coal_block"
    if block_id == 179:
        return {
            0: "minecraft:red_sandstone",
            1: "minecraft:chiseled_red_sandstone",
            2: "minecraft:smooth_red_sandstone",
        }.get(data)
    if block_id == 180:
        return _legacy_stair_state("red_sandstone", data)
    if block_id == 181:
        return _legacy_red_sandstone_slab_state(data, doubled=True)
    if block_id == 182:
        return _legacy_red_sandstone_slab_state(data, doubled=False)
    if block_id == 201:
        return "minecraft:purpur_block"
    if block_id == 202:
        return {
            0: "minecraft:purpur_pillar[axis=y]",
            4: "minecraft:purpur_pillar[axis=x]",
            8: "minecraft:purpur_pillar[axis=z]",
        }.get(data)
    if block_id == 203:
        return _legacy_stair_state("purpur", data)
    if block_id == 204:
        return "minecraft:purpur_slab[type=double]"
    if block_id == 205:
        return "minecraft:purpur_slab[type=top]" if data & 0x08 else "minecraft:purpur_slab[type=bottom]"
    if block_id == 206:
        return "minecraft:end_stone_bricks"
    if 235 <= block_id <= 250:
        color = COLOR_NAMES[block_id - 235]
        facing = HORIZONTAL_FACING.get(data & 0x03)
        if facing is None:
            return None
        return f"minecraft:{color}_glazed_terracotta[facing={facing}]"
    if block_id == 251 and data < len(COLOR_NAMES):
        return f"minecraft:{COLOR_NAMES[data]}_concrete"
    if block_id == 252 and data < len(COLOR_NAMES):
        return f"minecraft:{COLOR_NAMES[data]}_concrete_powder"
    return None


def _legacy_log_state(woods: tuple[str, ...], data: int) -> str | None:
    variant = data & 0x03
    if variant >= len(woods):
        return None

    wood = woods[variant]
    axis_bits = (data >> 2) & 0x03
    if axis_bits == 3:
        return f"minecraft:{wood}_wood"
    axis = AXES.get(axis_bits)
    if axis is None:
        return None
    return f"minecraft:{wood}_log[axis={axis}]"


def _legacy_leaves_state(woods: tuple[str, ...], data: int) -> str | None:
    variant = data & 0x03
    if variant >= len(woods):
        return None

    wood = woods[variant]
    if data & 0x04:
        return f"minecraft:{wood}_leaves[persistent=true]"
    return f"minecraft:{wood}_leaves"


def _legacy_stair_state(base: str, data: int) -> str | None:
    facing = STAIR_DIRECTIONS.get(data & 0x03)
    if facing is None:
        return None
    half = "top" if data & 0x04 else "bottom"
    return f"minecraft:{base}_stairs[facing={facing},half={half},shape=straight]"


def _legacy_stone_slab_state(data: int, *, doubled: bool) -> str | None:
    variant = data & 0x07
    slab_type = "double" if doubled else "top" if data & 0x08 else "bottom"
    base = {
        0: "stone",
        1: "sandstone",
        2: "oak",
        3: "cobblestone",
        4: "brick",
        5: "stone_brick",
        6: "nether_brick",
        7: "quartz",
    }.get(variant)
    if base is None:
        return None
    return f"minecraft:{base}_slab[type={slab_type}]"


def _legacy_wood_slab_state(data: int, *, doubled: bool) -> str | None:
    variant = data & 0x07
    if variant >= len(WOOD_NAMES):
        return None
    slab_type = "double" if doubled else "top" if data & 0x08 else "bottom"
    return f"minecraft:{WOOD_NAMES[variant]}_slab[type={slab_type}]"


def _legacy_red_sandstone_slab_state(data: int, *, doubled: bool) -> str:
    slab_type = "double" if doubled else "top" if data & 0x08 else "bottom"
    return f"minecraft:red_sandstone_slab[type={slab_type}]"


def _unknown_named_state(name: str, data: int) -> str:
    if data == 0:
        return name
    if "[" in name and name.endswith("]"):
        return name[:-1] + f",legacy_data={data}]"
    return f"{name}[legacy_data={data}]"
