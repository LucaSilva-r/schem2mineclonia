# schem2mineclonia

Standalone Python tool that converts modern Minecraft Sponge schematics
(`.schem`) into Luanti `.mts` schematics with Mineclonia node names.

It uses the Luanti MTS v4 format and a Mineclonia-oriented block mapper that
is partly inspired by `MC2MT/src/conversions.h`, but adapted to modern
post-flattening Minecraft blockstate names.

## What It Does

- reads Sponge schematic versions 2 and 3
- maps Minecraft blockstates to Mineclonia itemstrings
- preserves common orientation data for:
  - logs / wood blocks via `axis`
  - glazed terracotta via `facing`
  - common stairs and slabs
  - copper cut stairs and slabs
- writes a Luanti `.mts` schematic

## Current Limits

- legacy pre-Sponge `.schematic` files are not supported yet
- block entities and entities are ignored
  - MTS stores node names, `param1`, and `param2`, but not node metadata
- unsupported blocks are skipped by default
  - they become non-placing `air` entries so placement is safer

## Usage

From the repo root:

```bash
PYTHONPATH=schem2mineclonia python3 -m schem2mineclonia input.schem output.mts
```

Strict mode fails on the first unsupported palette entry:

```bash
PYTHONPATH=schem2mineclonia python3 -m schem2mineclonia input.schem output.mts --strict
```

You can force unknown blocks to a fallback Mineclonia node instead of skipping
them:

```bash
PYTHONPATH=schem2mineclonia python3 -m schem2mineclonia input.schem output.mts --unknown-node mcl_core:stone
```

## Notes

- Output format reference:
  `https://docs.luanti.org/for-creators/luanti-schematic-file-format/`
- Input format reference:
  Sponge Schematic Specification v2/v3
