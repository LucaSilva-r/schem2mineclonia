"""Shared schematic model types."""

from __future__ import annotations

from dataclasses import dataclass


class UnsupportedSchematicFormat(ValueError):
    """Raised when the input is a Minecraft schematic we do not support."""


@dataclass(frozen=True)
class MinecraftSchematic:
    """A palette-based Minecraft schematic in Sponge block order."""

    width: int
    height: int
    length: int
    palette: list[str]
    block_indices: list[int]
    version: int
    data_version: int | None
    block_entities_count: int
    entities_count: int
    offset: tuple[int, int, int]
