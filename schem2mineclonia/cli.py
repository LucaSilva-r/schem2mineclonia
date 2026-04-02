"""CLI entry point for schem2mineclonia."""

from __future__ import annotations

import argparse
from pathlib import Path

from .mapping import MinecloniaMapper
from .mts import write_mts
from .sponge import UnsupportedSchematicFormat, load_schematic


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert Minecraft .schem, .schematic, and .litematic files to Mineclonia .mts schematics."
    )
    parser.add_argument(
        "input",
        help="Input Minecraft schematic (.schem, .schematic, or .litematic)",
    )
    parser.add_argument(
        "output",
        nargs="?",
        help="Output Luanti schematic (.mts). Defaults to INPUT stem + .mts.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any Minecraft palette entry is unsupported.",
    )
    parser.add_argument(
        "--unknown-node",
        help="Fallback Mineclonia node for unsupported blocks. "
        "Without this, unsupported blocks are skipped safely.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".mts")

    try:
        schematic = load_schematic(input_path)
    except UnsupportedSchematicFormat as exc:
        parser.error(str(exc))

    mapper = MinecloniaMapper(unknown_node=args.unknown_node)
    mapped_palette, report = mapper.map_palette(
        schematic.palette,
        schematic.block_indices,
        block_entities_ignored=schematic.block_entities_count,
        entities_ignored=schematic.entities_count,
    )

    if args.strict and report.unknown_palette_states:
        parser.error(_format_unknown_summary(report))

    write_mts(
        output_path,
        width=schematic.width,
        height=schematic.height,
        length=schematic.length,
        block_indices=schematic.block_indices,
        mapped_palette=mapped_palette,
    )

    print(
        f"Wrote {output_path} "
        f"({schematic.width}x{schematic.height}x{schematic.length}, "
        f"{report.input_palette_size} palette entries, "
        f"{report.output_name_count} output node names)"
    )

    if report.block_entities_ignored:
        print(f"Ignored {report.block_entities_ignored} block entities")
    if report.entities_ignored:
        print(f"Ignored {report.entities_ignored} entities")
    if report.unknown_palette_states:
        print(_format_unknown_summary(report))

    return 0


def _format_unknown_summary(report) -> str:
    lines = [
        "Unsupported Minecraft blockstates were skipped"
        if report.unknown_block_count
        else "Unsupported Minecraft blockstates were found",
        f"  palette entries: {len(report.unknown_palette_states)}",
        f"  affected blocks: {report.unknown_block_count}",
    ]
    for state, count in report.unknown_palette_states[:20]:
        lines.append(f"  {count:>7}  {state}")
    if len(report.unknown_palette_states) > 20:
        lines.append(
            f"  ... and {len(report.unknown_palette_states) - 20} more palette entries"
        )
    return "\n".join(lines)
