"""Map Minecraft blockstates to Mineclonia nodes."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


AIR_LIKE = {"air", "cave_air", "void_air"}
SKIP_LIKE = {"structure_void", "barrier", "light"}
FACEDIR_4 = {"north": 0, "east": 1, "south": 2, "west": 3}
AXIS_PARAM2 = {"y": 0, "z": 4, "x": 12}
STAIR_BOTTOM_PARAM2 = {"north": 0, "east": 1, "south": 2, "west": 3}
STAIR_TOP_PARAM2 = {"north": 20, "east": 23, "south": 22, "west": 21}
COLOR_ALIASES = {"gray": "grey", "light_gray": "silver"}
WOOD_ALIASES = {"cherry": "cherry_blossom"}
CRIMSON_STEMS = {"crimson_stem": "crimson", "warped_stem": "warped"}
HYPHAE_BLOCKS = {"crimson_hyphae": "crimson", "warped_hyphae": "warped"}


DIRECT_NODE_MAP = {
    # Closely aligned with MC2MT's direct full-block mappings.
    "stone": "mcl_core:stone",
    "granite": "mcl_core:granite",
    "polished_granite": "mcl_core:granite_smooth",
    "diorite": "mcl_core:diorite",
    "polished_diorite": "mcl_core:diorite_smooth",
    "andesite": "mcl_core:andesite",
    "polished_andesite": "mcl_core:andesite_smooth",
    "grass_block": "mcl_core:dirt_with_grass",
    "dirt": "mcl_core:dirt",
    "coarse_dirt": "mcl_core:coarse_dirt",
    "podzol": "mcl_core:podzol",
    "cobblestone": "mcl_core:cobble",
    "mossy_cobblestone": "mcl_core:mossycobble",
    "bedrock": "mcl_core:bedrock",
    "sand": "mcl_core:sand",
    "red_sand": "mcl_core:redsand",
    "gravel": "mcl_core:gravel",
    "glass": "mcl_core:glass",
    "clay": "mcl_core:clay",
    "bricks": "mcl_core:brick_block",
    "obsidian": "mcl_core:obsidian",
    "crying_obsidian": "mcl_core:crying_obsidian",
    "stone_bricks": "mcl_core:stonebrick",
    "cracked_stone_bricks": "mcl_core:stonebrickcracked",
    "mossy_stone_bricks": "mcl_core:stonebrickmossy",
    "chiseled_stone_bricks": "mcl_core:stonebrickcarved",
    "smooth_stone": "mcl_core:stone_smooth",
    "sandstone": "mcl_core:sandstone",
    "cut_sandstone": "mcl_core:sandstone",
    "chiseled_sandstone": "mcl_core:sandstonecarved",
    "smooth_sandstone": "mcl_core:sandstonesmooth",
    "red_sandstone": "mcl_core:redsandstone",
    "cut_red_sandstone": "mcl_core:redsandstone",
    "chiseled_red_sandstone": "mcl_core:redsandstonecarved",
    "smooth_red_sandstone": "mcl_core:redsandstonesmooth",
    "snow_block": "mcl_core:snowblock",
    "ice": "mcl_core:ice",
    "packed_ice": "mcl_core:packed_ice",
    "coal_block": "mcl_core:coalblock",
    "iron_block": "mcl_core:ironblock",
    "gold_block": "mcl_core:goldblock",
    "diamond_block": "mcl_core:diamondblock",
    "lapis_block": "mcl_core:lapisblock",
    "emerald_block": "mcl_core:emeraldblock",
    "coal_ore": "mcl_core:stone_with_coal",
    "iron_ore": "mcl_core:stone_with_iron",
    "gold_ore": "mcl_core:stone_with_gold",
    "lapis_ore": "mcl_core:stone_with_lapis",
    "diamond_ore": "mcl_core:stone_with_diamond",
    "emerald_ore": "mcl_core:stone_with_emerald",
    "redstone_ore": "mcl_core:stone_with_redstone",
    "deepslate": "mcl_deepslate:deepslate",
    "cobbled_deepslate": "mcl_deepslate:deepslate_cobbled",
    "polished_deepslate": "mcl_deepslate:deepslate_polished",
    "deepslate_bricks": "mcl_deepslate:deepslate_bricks",
    "cracked_deepslate_bricks": "mcl_deepslate:deepslate_bricks_cracked",
    "deepslate_tiles": "mcl_deepslate:deepslate_tiles",
    "cracked_deepslate_tiles": "mcl_deepslate:deepslate_tiles_cracked",
    "chiseled_deepslate": "mcl_deepslate:deepslate_chiseled",
    "deepslate_coal_ore": "mcl_deepslate:deepslate_with_coal",
    "deepslate_iron_ore": "mcl_deepslate:deepslate_with_iron",
    "deepslate_gold_ore": "mcl_deepslate:deepslate_with_gold",
    "deepslate_lapis_ore": "mcl_deepslate:deepslate_with_lapis",
    "deepslate_diamond_ore": "mcl_deepslate:deepslate_with_diamond",
    "deepslate_emerald_ore": "mcl_deepslate:deepslate_with_emerald",
    "deepslate_redstone_ore": "mcl_deepslate:deepslate_with_redstone",
    "tuff": "mcl_deepslate:tuff",
    "tuff_bricks": "mcl_deepslate:tuff_bricks",
    "chiseled_tuff": "mcl_deepslate:tuff_chiseled",
    "chiseled_tuff_bricks": "mcl_deepslate:tuff_chiseled_bricks",
    "calcite": "mcl_amethyst:calcite",
    "amethyst_block": "mcl_amethyst:amethyst_block",
    "budding_amethyst": "mcl_amethyst:budding_amethyst_block",
    "beacon": "mcl_beacons:beacon",
    "end_stone": "mcl_end:end_stone",
    "end_stone_bricks": "mcl_end:end_bricks",
    "purpur_block": "mcl_end:purpur_block",
    "purpur_pillar": "mcl_end:purpur_pillar",
    "netherrack": "mcl_nether:netherrack",
    "soul_sand": "mcl_nether:soul_sand",
    "quartz_block": "mcl_nether:quartz_block",
    "chiseled_quartz_block": "mcl_nether:quartz_chiseled",
    "smooth_quartz": "mcl_nether:quartz_smooth",
    "prismarine": "mcl_ocean:prismarine",
    "prismarine_bricks": "mcl_ocean:prismarine_brick",
    "dark_prismarine": "mcl_ocean:prismarine_dark",
    "sea_lantern": "mcl_ocean:sea_lantern",
    "crafting_table": "mcl_crafting_table:crafting_table",
    "bookshelf": "mcl_books:bookshelf",
    "note_block": "mcl_noteblock:noteblock",
    "jukebox": "mcl_jukebox:jukebox",
    "moss_block": "mcl_lush_caves:moss",
    "dripstone_block": "mcl_dripstone:dripstone_block",
}


STAIR_MATERIALS = {
    "stone": "stone",
    "cobblestone": "cobble",
    "mossy_cobblestone": "mossycobble",
    "stone_bricks": "stonebrick",
    "mossy_stone_bricks": "stonebrickmossy",
    "granite": "granite",
    "polished_granite": "granite_smooth",
    "diorite": "diorite",
    "polished_diorite": "diorite_smooth",
    "andesite": "andesite",
    "polished_andesite": "andesite_smooth",
    "sandstone": "sandstone",
    "smooth_sandstone": "sandstonesmooth",
    "red_sandstone": "redsandstone",
    "smooth_red_sandstone": "redsandstonesmooth",
    "bricks": "brick_block",
    "nether_bricks": "nether_brick",
    "red_nether_bricks": "red_nether_brick",
    "quartz_block": "quartz_block",
    "smooth_quartz": "quartz_smooth",
    "end_stone_bricks": "end_bricks",
    "purpur_block": "purpur_block",
    "cobbled_deepslate": "deepslate_cobbled",
    "polished_deepslate": "deepslate_polished",
    "deepslate_bricks": "deepslate_bricks",
    "deepslate_tiles": "deepslate_tiles",
    "prismarine": "prismarine",
    "prismarine_bricks": "prismarine_brick",
    "dark_prismarine": "prismarine_dark",
}


@dataclass(frozen=True)
class ParsedBlockState:
    raw: str
    namespace: str
    name: str
    properties: dict[str, str]


@dataclass(frozen=True)
class MappedNode:
    name: str
    param1: int = 127
    param2: int = 0
    known: bool = True


@dataclass(frozen=True)
class ConversionReport:
    unknown_palette_states: tuple[tuple[str, int], ...]
    unknown_block_count: int
    block_entities_ignored: int
    entities_ignored: int
    input_palette_size: int
    output_name_count: int


class MinecloniaMapper:
    """State-aware mapper from Minecraft blockstates to Mineclonia nodes."""

    def __init__(self, unknown_node: str | None = None) -> None:
        self.unknown_node = unknown_node

    def map_palette(
        self,
        palette: Iterable[str],
        block_indices: Iterable[int],
        *,
        block_entities_ignored: int,
        entities_ignored: int,
    ) -> tuple[list[MappedNode], ConversionReport]:
        palette_list = list(palette)
        mapped = [self.map_blockstate(state) for state in palette_list]
        usage = Counter(block_indices)

        unknown_states: list[tuple[str, int]] = []
        unknown_blocks = 0
        for index, result in enumerate(mapped):
            if result.known:
                continue
            count = usage.get(index, 0)
            unknown_blocks += count
            unknown_states.append((palette_list[index], count))

        unknown_states.sort(key=lambda item: (-item[1], item[0]))
        output_name_count = len({node.name for node in mapped})

        report = ConversionReport(
            unknown_palette_states=tuple(unknown_states),
            unknown_block_count=unknown_blocks,
            block_entities_ignored=block_entities_ignored,
            entities_ignored=entities_ignored,
            input_palette_size=len(palette_list),
            output_name_count=output_name_count,
        )
        return mapped, report

    def map_blockstate(self, raw_state: str) -> MappedNode:
        block = parse_blockstate(raw_state)
        if block.namespace != "minecraft":
            return self._unknown()

        if block.name in AIR_LIKE:
            return MappedNode("air")
        if block.name in SKIP_LIKE:
            return MappedNode("air", param1=0)

        mapped = (
            self._map_liquids(block)
            or self._map_wood_family(block)
            or self._map_color_family(block)
            or self._map_copper_family(block)
            or self._map_stair(block)
            or self._map_slab(block)
            or self._map_direct(block)
        )
        if mapped is not None:
            return mapped
        return self._unknown()

    def _map_direct(self, block: ParsedBlockState) -> MappedNode | None:
        node_name = DIRECT_NODE_MAP.get(block.name)
        if node_name is None:
            return None

        param2 = 0
        if block.name in {"deepslate", "purpur_pillar"}:
            param2 = axis_to_param2(block.properties.get("axis"))
        if block.name == "purpur_pillar":
            node_name = "mcl_end:purpur_pillar"
        return MappedNode(node_name, param2=param2)

    def _map_liquids(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name == "water":
            if block.properties.get("level", "0") == "0":
                return MappedNode("mcl_core:water_source")
            return MappedNode("mcl_core:water_flowing")
        if block.name == "lava":
            if block.properties.get("level", "0") == "0":
                return MappedNode("mcl_core:lava_source")
            return MappedNode("mcl_core:lava_flowing")
        return None

    def _map_color_family(self, block: ParsedBlockState) -> MappedNode | None:
        name = block.name

        if name == "terracotta":
            return MappedNode("mcl_colorblocks:hardened_clay")
        if name == "glass":
            return MappedNode("mcl_core:glass")

        if name.endswith("_glazed_terracotta"):
            color = normalize_color(name[: -len("_glazed_terracotta")])
            param2 = direction_to_facedir(block.properties.get("facing"))
            return MappedNode(
                f"mcl_colorblocks:glazed_terracotta_{color}",
                param2=param2,
            )

        for suffix, template in (
            ("_wool", "mcl_wool:{color}"),
            ("_terracotta", "mcl_colorblocks:hardened_clay_{color}"),
            ("_concrete", "mcl_colorblocks:concrete_{color}"),
            ("_concrete_powder", "mcl_colorblocks:concrete_powder_{color}"),
            ("_stained_glass", "mcl_core:glass_{color}"),
        ):
            if name.endswith(suffix):
                color = normalize_color(name[: -len(suffix)])
                return MappedNode(template.format(color=color))

        return None

    def _map_wood_family(self, block: ParsedBlockState) -> MappedNode | None:
        name = block.name

        if name.endswith("_planks"):
            wood = normalize_wood(name[: -len("_planks")])
            return MappedNode(f"mcl_trees:wood_{wood}")

        if name.endswith("_sapling"):
            wood = normalize_wood(name[: -len("_sapling")])
            return MappedNode(f"mcl_trees:sapling_{wood}")

        if name.endswith("_leaves"):
            wood = normalize_wood(name[: -len("_leaves")])
            suffix = "_orphan" if block.properties.get("persistent") == "true" else ""
            return MappedNode(f"mcl_trees:leaves_{wood}{suffix}")

        special = CRIMSON_STEMS.get(name)
        if special is not None:
            return MappedNode(
                f"mcl_trees:tree_{special}",
                param2=axis_to_param2(block.properties.get("axis")),
            )

        special = HYPHAE_BLOCKS.get(name)
        if special is not None:
            return MappedNode(
                f"mcl_trees:bark_{special}",
                param2=axis_to_param2(block.properties.get("axis")),
            )

        match = re.fullmatch(r"stripped_(.+)_(log|stem)", name)
        if match:
            wood = normalize_wood(match.group(1))
            return MappedNode(
                f"mcl_trees:stripped_{wood}",
                param2=axis_to_param2(block.properties.get("axis")),
            )

        match = re.fullmatch(r"stripped_(.+)_(wood|hyphae)", name)
        if match:
            wood = normalize_wood(match.group(1))
            return MappedNode(
                f"mcl_trees:bark_stripped_{wood}",
                param2=axis_to_param2(block.properties.get("axis")),
            )

        match = re.fullmatch(r"(.+)_(log|stem)", name)
        if match:
            wood = normalize_wood(match.group(1))
            return MappedNode(
                f"mcl_trees:tree_{wood}",
                param2=axis_to_param2(block.properties.get("axis")),
            )

        match = re.fullmatch(r"(.+)_(wood|hyphae)", name)
        if match:
            wood = normalize_wood(match.group(1))
            return MappedNode(
                f"mcl_trees:bark_{wood}",
                param2=axis_to_param2(block.properties.get("axis")),
            )

        if name == "bamboo_block":
            return MappedNode(
                "mcl_trees:tree_bamboo",
                param2=axis_to_param2(block.properties.get("axis")),
            )
        if name == "stripped_bamboo_block":
            return MappedNode(
                "mcl_trees:stripped_bamboo",
                param2=axis_to_param2(block.properties.get("axis")),
            )

        return None

    def _map_copper_family(self, block: ParsedBlockState) -> MappedNode | None:
        name = block.name
        match = re.fullmatch(
            r"(waxed_)?(?:(exposed|weathered|oxidized)_)?(?:(cut|chiseled|grate)_)?copper(?:_block)?(?:_(stairs|slab))?",
            name,
        )
        if not match:
            return None

        waxed, stage_name, variant, shape = match.groups()
        stage = {
            None: "",
            "exposed": "_exposed",
            "weathered": "_weathered",
            "oxidized": "_oxidized",
        }[stage_name]
        variant = variant or ""
        preserved = ""
        if waxed:
            preserved = "" if stage_name == "oxidized" else "_preserved"

        if shape is None:
            if not variant:
                return MappedNode(f"mcl_copper:block{stage}{preserved}")
            return MappedNode(f"mcl_copper:block{stage}_{variant}{preserved}")

        if variant != "cut":
            return None

        if shape == "stairs":
            stair_suffix = ""
            stair_shape = block.properties.get("shape", "straight")
            if stair_shape.startswith("inner_"):
                stair_suffix = "_inner"
            elif stair_shape.startswith("outer_"):
                stair_suffix = "_outer"

            half = block.properties.get("half", "bottom")
            facing = block.properties.get("facing")
            param2 = stair_param2(facing, half)
            return MappedNode(
                f"mcl_stairs:stair_copper{stage}_cut{stair_suffix}{preserved}",
                param2=param2,
            )

        slab_type = block.properties.get("type", "bottom")
        slab_suffix = {"bottom": "", "top": "_top", "double": "_double"}.get(
            slab_type,
            "",
        )
        return MappedNode(
            f"mcl_stairs:slab_copper{stage}_cut{slab_suffix}{preserved}"
        )

    def _map_stair(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_stairs"):
            return None

        base = block.name[: -len("_stairs")]
        if base.endswith("_cut_copper") or base.endswith("_chiseled_copper") or base.endswith("_grate_copper"):
            return None

        material = None
        if base.endswith("_planks"):
            material = normalize_wood(base[: -len("_planks")])
        else:
            material = STAIR_MATERIALS.get(base)

        if material is None:
            return None

        stair_shape = block.properties.get("shape", "straight")
        stair_suffix = ""
        if stair_shape.startswith("inner_"):
            stair_suffix = "_inner"
        elif stair_shape.startswith("outer_"):
            stair_suffix = "_outer"

        half = block.properties.get("half", "bottom")
        facing = block.properties.get("facing")
        param2 = stair_param2(facing, half)
        return MappedNode(f"mcl_stairs:stair_{material}{stair_suffix}", param2=param2)

    def _map_slab(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_slab"):
            return None

        base = block.name[: -len("_slab")]
        if base.endswith("_cut_copper") or base.endswith("_chiseled_copper") or base.endswith("_grate_copper"):
            return None

        material = None
        if base.endswith("_planks"):
            material = normalize_wood(base[: -len("_planks")])
        else:
            material = STAIR_MATERIALS.get(base)

        if material is None:
            return None

        slab_type = block.properties.get("type", "bottom")
        suffix = {"bottom": "", "top": "_top", "double": "_double"}.get(
            slab_type,
            "",
        )
        return MappedNode(f"mcl_stairs:slab_{material}{suffix}")

    def _unknown(self) -> MappedNode:
        if self.unknown_node:
            return MappedNode(self.unknown_node, known=False)
        return MappedNode("air", param1=0, known=False)


def parse_blockstate(raw_state: str) -> ParsedBlockState:
    state = raw_state
    props: dict[str, str] = {}

    if "[" in state and state.endswith("]"):
        base, raw_props = state[:-1].split("[", 1)
        if raw_props:
            for item in raw_props.split(","):
                key, value = item.split("=", 1)
                props[key] = value
    else:
        base = state

    if ":" in base:
        namespace, name = base.split(":", 1)
    else:
        namespace, name = "minecraft", base
    return ParsedBlockState(raw=raw_state, namespace=namespace, name=name, properties=props)


def normalize_color(color: str) -> str:
    return COLOR_ALIASES.get(color, color)


def normalize_wood(wood: str) -> str:
    if wood in CRIMSON_STEMS:
        return CRIMSON_STEMS[wood]
    if wood in HYPHAE_BLOCKS:
        return HYPHAE_BLOCKS[wood]
    return WOOD_ALIASES.get(wood, wood)


def axis_to_param2(axis: str | None) -> int:
    return AXIS_PARAM2.get(axis or "y", 0)


def direction_to_facedir(direction: str | None) -> int:
    return FACEDIR_4.get(direction or "north", 0)


def stair_param2(direction: str | None, half: str | None) -> int:
    direction = direction or "north"
    if half == "top":
        return STAIR_TOP_PARAM2.get(direction, 20)
    return STAIR_BOTTOM_PARAM2.get(direction, 0)
