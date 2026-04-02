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
WALLMOUNT_PARAM2 = {"down": 0, "up": 1, "west": 2, "east": 3, "south": 4, "north": 5}
COLOR_ALIASES = {"gray": "grey", "light_gray": "silver"}
PANE_COLOR_ALIASES = {"gray": "grey", "light_gray": "silver"}
SHULKER_COLOR_ALIASES = {
    "gray": "dark_grey",
    "green": "dark_green",
    "light_blue": "lightblue",
    "light_gray": "grey",
    "lime": "green",
    "purple": "violet",
}
WOOD_ALIASES = {"cherry": "cherry_blossom"}
CRIMSON_STEMS = {"crimson_stem": "crimson", "warped_stem": "warped"}
HYPHAE_BLOCKS = {"crimson_hyphae": "crimson", "warped_hyphae": "warped"}
WOOD_FAMILY_BASES = {
    "oak",
    "spruce",
    "birch",
    "jungle",
    "acacia",
    "dark_oak",
    "mangrove",
    "cherry",
    "bamboo",
    "crimson",
    "warped",
    "pale_oak",
}
WOOD_STAIR_BASES = set(WOOD_FAMILY_BASES)
STAIR_BASE_ALIASES = {
    "brick": "bricks",
    "cut_red_sandstone": "red_sandstone",
    "cut_sandstone": "sandstone",
    "stone_brick": "stone_bricks",
    "mossy_stone_brick": "mossy_stone_bricks",
    "nether_brick": "nether_bricks",
    "red_nether_brick": "red_nether_bricks",
    "end_stone_brick": "end_stone_bricks",
    "prismarine_brick": "prismarine_bricks",
    "deepslate_brick": "deepslate_bricks",
    "deepslate_tile": "deepslate_tiles",
    "mud_brick": "mud_bricks",
    "polished_blackstone_brick": "polished_blackstone_bricks",
    "petrified_oak": "oak",
    "quartz": "quartz_block",
    "purpur": "purpur_block",
    "smooth_stone": "stone",
}
WALL_MATERIALS = {
    "cobblestone": "cobble",
    "mossy_cobblestone": "mossycobble",
    "andesite": "andesite",
    "granite": "granite",
    "diorite": "diorite",
    "brick": "brick",
    "sandstone": "sandstone",
    "red_sandstone": "redsandstone",
    "stone_brick": "stonebrick",
    "mossy_stone_brick": "stonebrickmossy",
    "prismarine": "prismarine",
    "end_stone_brick": "endbricks",
    "nether_brick": "netherbrick",
    "red_nether_brick": "rednetherbrick",
    "mud_brick": "mudbrick",
}
FLOWER_NODE_MAP = {
    "allium": "mcl_flowers:allium",
    "azure_bluet": "mcl_flowers:azure_bluet",
    "blue_orchid": "mcl_flowers:blue_orchid",
    "closed_eyeblossom": "mcl_flowers:eyeblossom",
    "cornflower": "mcl_flowers:cornflower",
    "crimson_fungus": "mcl_crimson:crimson_fungus",
    "crimson_nylium": "mcl_crimson:crimson_nylium",
    "crimson_roots": "mcl_crimson:crimson_roots",
    "dandelion": "mcl_flowers:dandelion",
    "lily_of_the_valley": "mcl_flowers:lily_of_the_valley",
    "nether_sprouts": "mcl_crimson:nether_sprouts",
    "open_eyeblossom": "mcl_flowers:eyeblossom_open",
    "orange_tulip": "mcl_flowers:tulip_orange",
    "oxeye_daisy": "mcl_flowers:oxeye_daisy",
    "pink_tulip": "mcl_flowers:tulip_pink",
    "red_tulip": "mcl_flowers:tulip_red",
    "warped_fungus": "mcl_crimson:warped_fungus",
    "warped_nylium": "mcl_crimson:warped_nylium",
    "warped_roots": "mcl_crimson:warped_roots",
    "warped_wart_block": "mcl_crimson:warped_wart_block",
    "white_tulip": "mcl_flowers:tulip_white",
    "wither_rose": "mcl_flowers:wither_rose",
    "brown_mushroom": "mcl_mushrooms:mushroom_brown",
    "red_mushroom": "mcl_mushrooms:mushroom_red",
}


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
    "mycelium": "mcl_core:mycelium",
    "podzol": "mcl_core:podzol",
    "dirt_path": "mcl_core:grass_path",
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
    "blue_ice": "mcl_core:blue_ice",
    "packed_ice": "mcl_core:packed_ice",
    "bone_block": "mcl_core:bone_block",
    "cobweb": "mcl_core:cobweb",
    "cactus": "mcl_core:cactus",
    "cactus_flower": "mcl_core:cactus_flower",
    "slime_block": "mcl_core:slimeblock",
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
    "tinted_glass": "mcl_amethyst:tinted_glass",
    "beacon": "mcl_beacons:beacon",
    "end_stone": "mcl_end:end_stone",
    "end_stone_bricks": "mcl_end:end_bricks",
    "purpur_block": "mcl_end:purpur_block",
    "purpur_pillar": "mcl_end:purpur_pillar",
    "netherrack": "mcl_nether:netherrack",
    "ancient_debris": "mcl_nether:ancient_debris",
    "nether_quartz_ore": "mcl_nether:quartz_ore",
    "netherite_block": "mcl_nether:netheriteblock",
    "magma_block": "mcl_nether:magma",
    "nether_wart_block": "mcl_nether:nether_wart_block",
    "nether_bricks": "mcl_nether:nether_brick",
    "red_nether_bricks": "mcl_nether:red_nether_brick",
    "chiseled_nether_bricks": "mcl_nether:chiseled_nether_brick",
    "cracked_nether_bricks": "mcl_nether:cracked_nether_brick",
    "soul_sand": "mcl_nether:soul_sand",
    "nether_gold_ore": "mcl_blackstone:nether_gold",
    "quartz_block": "mcl_nether:quartz_block",
    "chiseled_quartz_block": "mcl_nether:quartz_chiseled",
    "quartz_pillar": "mcl_nether:quartz_pillar",
    "smooth_quartz": "mcl_nether:quartz_smooth",
    "blackstone": "mcl_blackstone:blackstone",
    "gilded_blackstone": "mcl_blackstone:blackstone_gilded",
    "polished_blackstone": "mcl_blackstone:blackstone_polished",
    "chiseled_polished_blackstone": "mcl_blackstone:blackstone_chiseled_polished",
    "polished_blackstone_bricks": "mcl_blackstone:blackstone_brick_polished",
    "basalt": "mcl_blackstone:basalt",
    "polished_basalt": "mcl_blackstone:basalt_polished",
    "smooth_basalt": "mcl_blackstone:basalt_smooth",
    "soul_soil": "mcl_blackstone:soul_soil",
    "prismarine": "mcl_ocean:prismarine",
    "prismarine_bricks": "mcl_ocean:prismarine_brick",
    "dark_prismarine": "mcl_ocean:prismarine_dark",
    "sea_lantern": "mcl_ocean:sea_lantern",
    "glowstone": "mcl_nether:glowstone",
    "crafting_table": "mcl_crafting_table:crafting_table",
    "bookshelf": "mcl_books:bookshelf",
    "flower_pot": "mcl_flowerpots:flower_pot",
    "note_block": "mcl_noteblock:noteblock",
    "jukebox": "mcl_jukebox:jukebox",
    "sponge": "mcl_sponges:sponge",
    "wet_sponge": "mcl_sponges:sponge_wet",
    "moss_block": "mcl_lush_caves:moss",
    "azalea": "mcl_lush_caves:azalea",
    "flowering_azalea": "mcl_lush_caves:azalea_flowering",
    "rooted_dirt": "mcl_lush_caves:rooted_dirt",
    "hanging_roots": "mcl_lush_caves:hanging_roots",
    "spore_blossom": "mcl_lush_caves:spore_blossom",
    "mangrove_roots": "mcl_mangrove:mangrove_roots",
    "muddy_mangrove_roots": "mcl_mangrove:mangrove_mud_roots",
    "mud": "mcl_mud:mud",
    "packed_mud": "mcl_mud:packed_mud",
    "dripstone_block": "mcl_dripstone:dripstone_block",
    "mud_bricks": "mcl_mud:mud_bricks",
    "hay_block": "mcl_farming:hay_block",
    "lodestone": "mcl_compass:lodestone",
    "dead_bush": "mcl_core:deadbush",
    "grass": "mcl_flowers:tallgrass",
    "short_grass": "mcl_flowers:tallgrass",
    "fern": "mcl_flowers:fern",
    "poppy": "mcl_flowers:poppy",
    "shroomlight": "mcl_crimson:shroomlight",
    "bamboo_mosaic": "mcl_bamboo:bamboo_mosaic",
    "scaffolding": "mcl_bamboo:scaffolding",
    "sugar_cane": "mcl_core:reeds",
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
    "mud_bricks": "mud_brick",
    "blackstone": "blackstone",
    "polished_blackstone": "blackstone_polished",
    "polished_blackstone_bricks": "blackstone_brick_polished",
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
            or self._map_infested(block)
            or self._map_torch(block)
            or self._map_lightning_rod(block)
            or self._map_banner(block)
            or self._map_item_frame(block)
            or self._map_amethyst(block)
            or self._map_utility_block(block)
            or self._map_wall(block)
            or self._map_pane(block)
            or self._map_coral(block)
            or self._map_tall_plant(block)
            or self._map_farm_block(block)
            or self._map_lush_caves(block)
            or self._map_flower(block)
            or self._map_sign(block)
            or self._map_bed(block)
            or self._map_shulker_box(block)
            or self._map_fence(block)
            or self._map_fence_gate(block)
            or self._map_button(block)
            or self._map_pressure_plate(block)
            or self._map_door(block)
            or self._map_trapdoor(block)
            or self._map_copper_decor(block)
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
        if block.name in {"bone_block", "deepslate", "hay_block", "purpur_pillar", "quartz_pillar"}:
            param2 = axis_to_param2(block.properties.get("axis"))
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

    def _map_infested(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.startswith("infested_"):
            return None

        mapped = self.map_blockstate(f"minecraft:{block.name[len('infested_'):]}")
        if mapped.known:
            return mapped
        return None

    def _map_color_family(self, block: ParsedBlockState) -> MappedNode | None:
        name = block.name

        if name == "terracotta":
            return MappedNode("mcl_colorblocks:hardened_clay")
        if name == "glass":
            return MappedNode("mcl_core:glass")

        if name.endswith("_glazed_terracotta"):
            color = normalize_color(name[: -len("_glazed_terracotta")])
            return MappedNode(
                f"mcl_colorblocks:glazed_terracotta_{color}",
                param2=direction_to_facedir(block.properties.get("facing")),
            )

        for suffix, template in (
            ("_wool", "mcl_wool:{color}"),
            ("_carpet", "mcl_wool:{color}_carpet"),
            ("_terracotta", "mcl_colorblocks:hardened_clay_{color}"),
            ("_concrete", "mcl_colorblocks:concrete_{color}"),
            ("_concrete_powder", "mcl_colorblocks:concrete_powder_{color}"),
            ("_stained_glass", "mcl_core:glass_{color}"),
        ):
            if name.endswith(suffix):
                color = normalize_color(name[: -len(suffix)])
                return MappedNode(template.format(color=color))

        return None

    def _map_torch(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name == "torch":
            return MappedNode("mcl_torches:torch", param2=1)
        if block.name == "wall_torch":
            return MappedNode(
                "mcl_torches:torch_wall",
                param2=wallmounted_to_param2(block.properties.get("facing")),
            )
        if block.name == "copper_torch":
            return MappedNode("mcl_copper:copper_torch", param2=1)
        if block.name == "copper_wall_torch":
            return MappedNode(
                "mcl_copper:copper_torch_wall",
                param2=wallmounted_to_param2(block.properties.get("facing")),
            )
        if block.name == "redstone_torch":
            suffix = "on" if block.properties.get("lit", "true") == "true" else "off"
            return MappedNode(f"mcl_redstone_torch:redstone_torch_{suffix}", param2=1)
        if block.name == "redstone_wall_torch":
            suffix = "on" if block.properties.get("lit", "true") == "true" else "off"
            return MappedNode(
                f"mcl_redstone_torch:redstone_torch_{suffix}_wall",
                param2=wallmounted_to_param2(block.properties.get("facing")),
            )
        if block.name == "soul_torch":
            return MappedNode("mcl_blackstone:soul_torch", param2=1)
        if block.name == "soul_wall_torch":
            return MappedNode(
                "mcl_blackstone:soul_torch_wall",
                param2=wallmounted_to_param2(block.properties.get("facing")),
            )
        return None

    def _map_lightning_rod(self, block: ParsedBlockState) -> MappedNode | None:
        match = re.fullmatch(r"(waxed_)?(?:(exposed|weathered|oxidized)_)?lightning_rod", block.name)
        if not match:
            return None

        waxed, stage_name = match.groups()
        stage = copper_stage_suffix(stage_name)
        powered = "_powered" if block.properties.get("powered") == "true" else ""
        preserved = "_preserved" if waxed else ""
        return MappedNode(
            f"mcl_lightning_rods:rod{stage}{powered}{preserved}",
            param2=lightning_rod_param2(block.properties.get("facing")),
        )

    def _map_banner(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name.endswith("_wall_banner"):
            return MappedNode(
                "mcl_banners:hanging_banner",
                param2=wallmounted_to_param2(block.properties.get("facing")),
            )
        if block.name.endswith("_banner"):
            return MappedNode("mcl_banners:standing_banner")
        return None

    def _map_item_frame(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name == "item_frame":
            return MappedNode(
                "mcl_itemframes:item_frame",
                param2=wallmounted_to_param2(block.properties.get("facing")),
            )
        if block.name == "glow_item_frame":
            return MappedNode(
                "mcl_itemframes:glow_frame",
                param2=wallmounted_to_param2(block.properties.get("facing")),
            )
        return None

    def _map_amethyst(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name not in {
            "small_amethyst_bud",
            "medium_amethyst_bud",
            "large_amethyst_bud",
            "amethyst_cluster",
        }:
            return None

        return MappedNode(
            f"mcl_amethyst:{block.name}",
            param2=wallmounted_to_param2(block.properties.get("facing"), default="up"),
        )

    def _map_utility_block(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name == "barrel":
            return MappedNode(
                "mcl_barrels:barrel_closed",
                param2=direction_to_facedir(block.properties.get("facing")),
            )

        if block.name in {"beehive", "bee_nest"}:
            suffix = honey_level_suffix(block.properties.get("honey_level"))
            return MappedNode(
                f"mcl_beehives:{block.name}{suffix}",
                param2=direction_to_facedir(block.properties.get("facing")),
            )

        if block.name == "chiseled_bookshelf":
            return MappedNode(
                "mcl_books:chiseled_bookshelf",
                param2=direction_to_facedir(block.properties.get("facing")),
            )

        return None

    def _map_wall(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_wall"):
            return None

        base = block.name[: -len("_wall")]
        if base in {"blackstone", "polished_blackstone_brick"}:
            return MappedNode("mcl_blackstone:wall")

        material = WALL_MATERIALS.get(base)
        if material is None:
            return None
        return MappedNode(f"mcl_walls:{material}")

    def _map_pane(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name == "iron_bars":
            return MappedNode("mcl_panes:bar")
        if block.name == "glass_pane":
            return MappedNode("mcl_panes:pane_natural")
        if block.name.endswith("_stained_glass_pane"):
            color = pane_color(block.name[: -len("_stained_glass_pane")])
            return MappedNode(f"mcl_panes:pane_{color}")

        match = re.fullmatch(r"(waxed_)?(?:(exposed|weathered|oxidized)_)?copper_bars", block.name)
        if match:
            waxed, stage_name = match.groups()
            stage = copper_stage_suffix(stage_name)
            preserved = "_preserved" if waxed else ""
            return MappedNode(f"mcl_panes:copper_bar{stage}{preserved}")

        return None

    def _map_coral(self, block: ParsedBlockState) -> MappedNode | None:
        for suffix, target_suffix in (
            ("_coral_block", "_coral_block"),
            ("_coral_wall_fan", "_coral_fan"),
            ("_coral_fan", "_coral_fan"),
            ("_coral", "_coral"),
        ):
            if not block.name.endswith(suffix):
                continue

            base = block.name[: -len(suffix)]
            prefix = ""
            if base.startswith("dead_"):
                prefix = "dead_"
                base = base[len("dead_") :]
            return MappedNode(f"mcl_ocean:{prefix}{base}{target_suffix}")

        return None

    def _map_tall_plant(self, block: ParsedBlockState) -> MappedNode | None:
        aliases = {
            "large_fern": "double_fern",
            "tall_grass": "double_grass",
        }
        name = aliases.get(block.name, block.name)
        if name not in {
            "peony",
            "rose_bush",
            "lilac",
            "sunflower",
            "double_fern",
            "double_grass",
        }:
            return None

        suffix = "_top" if block.properties.get("half", "lower") == "upper" else ""
        return MappedNode(f"mcl_flowers:{name}{suffix}")

    def _map_farm_block(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name != "farmland":
            return None

        moisture = block.properties.get("moisture", "0")
        if moisture != "0":
            return MappedNode("mcl_farming:soil_wet")
        return MappedNode("mcl_farming:soil")

    def _map_lush_caves(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name in {"cave_vines", "cave_vines_plant"}:
            if block.properties.get("berries") == "true":
                return MappedNode("mcl_lush_caves:cave_vines_lit")
            return MappedNode("mcl_lush_caves:cave_vines")

        if block.name == "small_dripleaf":
            return MappedNode(
                "mcl_lush_caves:dripleaf_small",
                param2=direction_to_facedir(block.properties.get("facing")),
            )

        if block.name == "big_dripleaf":
            return MappedNode(
                "mcl_lush_caves:dripleaf_big",
                param2=direction_to_facedir(block.properties.get("facing")),
            )

        return None

    def _map_flower(self, block: ParsedBlockState) -> MappedNode | None:
        node_name = FLOWER_NODE_MAP.get(block.name)
        if node_name is None:
            return None
        return MappedNode(node_name)

    def _map_sign(self, block: ParsedBlockState) -> MappedNode | None:
        for suffix in ("_wall_hanging_sign", "_wall_sign", "_hanging_sign", "_sign"):
            if not block.name.endswith(suffix):
                continue

            wood = wood_family_name(block.name[: -len(suffix)])
            if wood is None:
                return None

            if suffix == "_wall_sign":
                return MappedNode(
                    f"mcl_signs:wall_sign_{wood}",
                    param2=wallmounted_to_param2(block.properties.get("facing")),
                )
            if suffix == "_sign":
                return MappedNode(
                    f"mcl_signs:standing_sign_{wood}",
                    param2=sign_rotation_to_param2(block.properties.get("rotation")),
                )
            if suffix == "_wall_hanging_sign":
                return MappedNode(
                    f"mcl_signs:hanging_sign_wall_{wood}",
                    param2=direction_to_facedir(block.properties.get("facing")),
                )

            if block.properties.get("attached") == "true":
                return MappedNode(
                    f"mcl_signs:hanging_sign_attached_{wood}",
                    param2=sign_rotation_to_param2(block.properties.get("rotation")),
                )
            return MappedNode(
                f"mcl_signs:hanging_sign_{wood}",
                param2=rotation_to_fourdir(block.properties.get("rotation")),
            )

        return None

    def _map_bed(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_bed"):
            return None

        color = normalize_color(block.name[: -len("_bed")])
        part = "_top" if block.properties.get("part") == "head" else "_bottom"
        return MappedNode(
            f"mcl_beds:bed_{color}{part}",
            param2=direction_to_facedir(block.properties.get("facing")),
        )

    def _map_shulker_box(self, block: ParsedBlockState) -> MappedNode | None:
        if block.name == "shulker_box":
            color = "violet"
        elif block.name.endswith("_shulker_box"):
            color = shulker_color(block.name[: -len("_shulker_box")])
        else:
            return None

        return MappedNode(
            f"mcl_chests:{color}_shulker_box",
            param2=direction_to_facedir(block.properties.get("facing")),
        )

    def _map_fence(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_fence"):
            return None

        base = block.name[: -len("_fence")]
        wood = wood_family_name(base)
        if wood is not None:
            return MappedNode(f"mcl_fences:{wood}_fence")
        if base in {"nether_brick", "red_nether_brick"}:
            return MappedNode(f"mcl_fences:{base}_fence")
        return None

    def _map_fence_gate(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_fence_gate"):
            return None

        base = block.name[: -len("_fence_gate")]
        wood = wood_family_name(base)
        if wood is not None:
            node_name = f"mcl_fences:{wood}_fence_gate"
        elif base in {"nether_brick", "red_nether_brick"}:
            node_name = f"mcl_fences:{base}_fence_gate"
        else:
            return None

        if block.properties.get("open") == "true":
            node_name += "_open"
        return MappedNode(
            node_name,
            param2=direction_to_facedir(block.properties.get("facing")),
        )

    def _map_button(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_button"):
            return None

        base = block.name[: -len("_button")]
        if base in {"stone", "polished_blackstone"}:
            button_base = base
        else:
            wood = wood_family_name(base)
            if wood is None:
                return None
            button_base = wood

        state = "on" if block.properties.get("powered") == "true" else "off"
        return MappedNode(
            f"mcl_buttons:button_{button_base}_{state}",
            param2=button_param2(
                block.properties.get("face"),
                block.properties.get("facing"),
            ),
        )

    def _map_pressure_plate(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_pressure_plate"):
            return None

        base = block.name[: -len("_pressure_plate")]
        if base in {"stone", "polished_blackstone"}:
            plate_base = base
        elif base == "light_weighted":
            plate_base = "light"
        elif base == "heavy_weighted":
            plate_base = "heavy"
        else:
            wood = wood_family_name(base)
            if wood is None:
                return None
            plate_base = wood

        suffix = "_on" if block.properties.get("powered") == "true" else "_off"
        return MappedNode(f"mcl_pressureplates:pressure_plate_{plate_base}{suffix}")

    def _map_door(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_door"):
            return None

        base = block.name[: -len("_door")]
        node_name = None
        wood = wood_family_name(base)
        if wood is not None:
            node_name = f"mcl_doors:door_{wood}"
        elif base == "iron":
            node_name = "mcl_doors:iron_door"
        else:
            match = re.fullmatch(r"(waxed_)?(?:(exposed|weathered|oxidized)_)?copper", base)
            if match:
                waxed, stage_name = match.groups()
                stage = copper_stage_suffix(stage_name)
                preserved = "_preserved" if waxed else ""
                node_name = f"mcl_copper:door{stage}{preserved}"

        if node_name is None:
            return None

        part = "t" if block.properties.get("half") == "upper" else "b"
        variant = door_variant(block.properties.get("hinge"))
        return MappedNode(
            f"{node_name}_{part}_{variant}",
            param2=direction_to_facedir(block.properties.get("facing")),
        )

    def _map_trapdoor(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_trapdoor"):
            return None

        base = block.name[: -len("_trapdoor")]
        node_name = None
        wood = wood_family_name(base)
        if wood is not None:
            node_name = f"mcl_doors:trapdoor_{wood}"
        elif base == "iron":
            node_name = "mcl_doors:iron_trapdoor"
        else:
            match = re.fullmatch(r"(waxed_)?(?:(exposed|weathered|oxidized)_)?copper", base)
            if match:
                waxed, stage_name = match.groups()
                stage = copper_stage_suffix(stage_name)
                preserved = "_preserved" if waxed else ""
                node_name = f"mcl_copper:trapdoor{stage}{preserved}"

        if node_name is None:
            return None

        if block.properties.get("open") == "true":
            node_name += "_open"

        param2 = direction_to_facedir(block.properties.get("facing"))
        if block.properties.get("half") == "top":
            param2 += 20
        return MappedNode(node_name, param2=param2)

    def _map_copper_decor(self, block: ParsedBlockState) -> MappedNode | None:
        match = re.fullmatch(r"(waxed_)?(?:(exposed|weathered|oxidized)_)?copper_grate", block.name)
        if match:
            waxed, stage_name = match.groups()
            stage = copper_stage_suffix(stage_name)
            preserved = "_preserved" if waxed else ""
            return MappedNode(f"mcl_copper:block{stage}_grate{preserved}")

        match = re.fullmatch(r"(waxed_)?(?:(exposed|weathered|oxidized)_)?copper_bulb", block.name)
        if not match:
            return None

        waxed, stage_name = match.groups()
        stage = copper_stage_suffix(stage_name)
        lit = "on" if block.properties.get("lit") == "true" else "off"
        powered = "_powered" if block.properties.get("powered") == "true" else ""
        preserved = "_preserved" if waxed else ""
        return MappedNode(f"mcl_copper:bulb{stage}_{lit}{powered}{preserved}")

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
        match = re.fullmatch(
            r"(waxed_)?(?:(exposed|weathered|oxidized)_)?(?:(cut|chiseled|grate)_)?copper(?:_block)?(?:_(stairs|slab))?",
            block.name,
        )
        if not match:
            return None

        waxed, stage_name, variant, shape = match.groups()
        stage = copper_stage_suffix(stage_name)
        variant = variant or ""
        preserved = "_preserved" if waxed else ""

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

            return MappedNode(
                f"mcl_stairs:stair_copper{stage}_cut{stair_suffix}{preserved}",
                param2=stair_param2(
                    block.properties.get("facing"),
                    block.properties.get("half", "bottom"),
                ),
            )

        slab_type = block.properties.get("type", "bottom")
        slab_suffix = {"bottom": "", "top": "_top", "double": "_double"}.get(
            slab_type,
            "",
        )
        return MappedNode(f"mcl_stairs:slab_copper{stage}_cut{slab_suffix}{preserved}")

    def _map_stair(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_stairs"):
            return None

        base = block.name[: -len("_stairs")]
        if base.endswith("_cut_copper") or base.endswith("_chiseled_copper") or base.endswith("_grate_copper"):
            return None

        material = stair_material(base)
        if material is None:
            return None

        stair_shape = block.properties.get("shape", "straight")
        stair_suffix = ""
        if stair_shape.startswith("inner_"):
            stair_suffix = "_inner"
        elif stair_shape.startswith("outer_"):
            stair_suffix = "_outer"

        return MappedNode(
            f"mcl_stairs:stair_{material}{stair_suffix}",
            param2=stair_param2(
                block.properties.get("facing"),
                block.properties.get("half", "bottom"),
            ),
        )

    def _map_slab(self, block: ParsedBlockState) -> MappedNode | None:
        if not block.name.endswith("_slab"):
            return None

        base = block.name[: -len("_slab")]
        if base.endswith("_cut_copper") or base.endswith("_chiseled_copper") or base.endswith("_grate_copper"):
            return None

        material = stair_material(base)
        if material is None:
            return None

        slab_type = block.properties.get("type", "bottom")
        suffix = {"bottom": "", "top": "_top", "double": "_double"}.get(slab_type, "")
        return MappedNode(f"mcl_stairs:slab_{material}{suffix}")

    def _unknown(self) -> MappedNode:
        if self.unknown_node:
            return MappedNode(self.unknown_node, known=False)
        return MappedNode("air", param1=0, known=False)


def parse_blockstate(raw_state: str) -> ParsedBlockState:
    props: dict[str, str] = {}
    state = raw_state

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


def pane_color(color: str) -> str:
    return PANE_COLOR_ALIASES.get(color, color)


def shulker_color(color: str) -> str:
    return SHULKER_COLOR_ALIASES.get(color, color)


def normalize_wood(wood: str) -> str:
    if wood in CRIMSON_STEMS:
        return CRIMSON_STEMS[wood]
    if wood in HYPHAE_BLOCKS:
        return HYPHAE_BLOCKS[wood]
    return WOOD_ALIASES.get(wood, wood)


def wood_family_name(wood: str) -> str | None:
    if wood not in WOOD_FAMILY_BASES:
        return None
    return normalize_wood(wood)


def axis_to_param2(axis: str | None) -> int:
    return AXIS_PARAM2.get(axis or "y", 0)


def stair_material(base: str) -> str | None:
    if base == "bamboo_mosaic":
        return "bamboo_mosaic"
    if base.endswith("_planks"):
        return normalize_wood(base[: -len("_planks")])
    if base in WOOD_STAIR_BASES:
        return normalize_wood(base)
    return STAIR_MATERIALS.get(STAIR_BASE_ALIASES.get(base, base))


def direction_to_facedir(direction: str | None) -> int:
    return FACEDIR_4.get(direction or "north", 0)


def wallmounted_to_param2(direction: str | None, *, default: str = "north") -> int:
    return WALLMOUNT_PARAM2.get(direction or default, WALLMOUNT_PARAM2[default])


def lightning_rod_param2(direction: str | None) -> int:
    return {
        "up": 0,
        "south": 4,
        "north": 8,
        "east": 12,
        "west": 16,
        "down": 20,
    }.get(direction or "up", 0)


def stair_param2(direction: str | None, half: str | None) -> int:
    direction = direction or "north"
    if half == "top":
        return STAIR_TOP_PARAM2.get(direction, 20)
    return STAIR_BOTTOM_PARAM2.get(direction, 0)


def sign_rotation_to_param2(rotation: str | None) -> int:
    try:
        return (int(rotation or "0") % 16) * 15
    except ValueError:
        return 0


def rotation_to_fourdir(rotation: str | None) -> int:
    try:
        return ((int(rotation or "0") % 16) + 2) // 4 % 4
    except ValueError:
        return 0


def button_param2(face: str | None, direction: str | None) -> int:
    if face == "ceiling":
        return wallmounted_to_param2("down")
    if face == "floor":
        return wallmounted_to_param2("up")
    return wallmounted_to_param2(direction)


def door_variant(hinge: str | None) -> int:
    return 2 if hinge == "right" else 1


def honey_level_suffix(level: str | None) -> str:
    try:
        amount = int(level or "0")
    except ValueError:
        return ""
    if amount <= 0:
        return ""
    if amount >= 5:
        return "_5"
    return f"_{amount}"


def copper_stage_suffix(stage_name: str | None) -> str:
    return {
        None: "",
        "exposed": "_exposed",
        "weathered": "_weathered",
        "oxidized": "_oxidized",
    }[stage_name]
