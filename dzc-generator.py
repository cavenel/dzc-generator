#!/usr/bin/env python3
"""
A literal – but ‘pythonic’ – translation of the C++ program that builds a
Deep-Zoom collection (.dzc) from a directory full of images.

The code uses
    • pathlib                     – modern, object–oriented paths
    • pyvips                      – Python binding for libvips
    • the standard library only   – no other dependencies

Author:  (Christophe Avenel)
"""

#from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Iterable

import pyvips                                       # sudo apt install libvips-dev python3-pyvips
from pyvips import Direction


# --------------------------------------------------------------------------- #
#                           Helper / utility functions                        #
# --------------------------------------------------------------------------- #
def list_images(path: Path) -> list[Path]:
    """Return all regular, *non-hidden* files inside *path* (no recursion)."""
    return [f for f in sorted(path.iterdir())
            if f.is_file() and not f.name.startswith('.')]


def morton_row_col(index: int, l: int) -> tuple[int, int]:
    """
    Convert a linear index to (row, col) using ‘Morton order’ (the bit-twiddling
    used by Deep-Zoom for naming tiles).
    """
    row = col = 0
    for i in range(l):
        row |= (index >> i) & (1 << i)
        col |= (index >> (i + 1)) & (1 << i)
    print (f'index={index}, row={row}, col={col}')  # debug output
    return row, col


def mkdir(path: Path) -> None:
    """`g_mkdir()` equivalent: create directory (and parents) if necessary."""
    path.mkdir(mode=0o777, parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
#                         Core collection building code                       #
# --------------------------------------------------------------------------- #
def build_collection(input_dir: str | Path,
                     output_dir: str | Path,
                     output_name: str) -> None:
    """
    Create a Deep-Zoom collection (.dzc) out of all images in *input_dir*.

    Parameters
    ----------
    input_dir   Directory that contains images (any format libvips can read).
    output_dir  Target directory. It will be created when necessary.
    output_name Base filename of the resulting collection (without extension).

    The resulting files are:
        {output_dir}/{output_name}.dzc                  – collection descriptor
        {output_dir}/{output_name}_files/{level}/…      – pyramid tiles
        {output_dir}/{id}.dzi + {output_dir}/{id}_files – one DZI per image
    """
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    mkdir(output_dir)

    images: list[Path] = list_images(input_dir)
    n_items: int = len(images)
    if n_items == 0:
        raise RuntimeError(f'No images found in "{input_dir}"')

    # ────────────────────────────── 1. high-level constants ────────────────── #
    max_level: int = int(math.log2(n_items))              # deepest level
    l: int = int(math.ceil(math.log2(n_items) / 2.0))     # helper used for morton

    tiles_root = output_dir / f'{output_name}_files'
    level_dir  = tiles_root / str(max_level)
    mkdir(level_dir)

    # ----------------------------------------------------------------------- #
    #                         2. create the .dzc file                         #
    # ----------------------------------------------------------------------- #
    dzc_path = output_dir / f'{output_name}.dzc'
    with dzc_path.open('w', encoding='utf-8') as dzc:
        dzc.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        dzc.write(f'<Collection MaxLevel="{max_level}" '
                  f'TileSize="256" Format="jpg" '
                  f'NextItemId="{n_items}" '
                  f'xmlns="http://schemas.microsoft.com/deepzoom/2008">\n')
        dzc.write('<Items>\n')

        # ------------------------------------------------------------------- #
        #               3. loop through every image in input_dir              #
        # ------------------------------------------------------------------- #
        for idx, img_path in enumerate(images):
            # ---- 3.1 load image with vips ---------------------------------- #
            image = pyvips.Image.new_from_file(str(img_path))

            # ---- 3.2 store a full Deep-Zoom image (dzi + tiles) ------------ #
            dzi_base = output_dir / str(idx)           # “0”, “1”, “2”… etc.
            image.dzsave(str(dzi_base))

            # ---- 3.3 create overview tile for deepest collection level ----- #
            width, height = image.width, image.height
            # shrink factor (power of 2) so that longest edge ≤ 256
            shrink_pow = math.ceil(math.log2(max(width, height) / 256.0))
            shrink_factor = 1 << shrink_pow

            small = (image
                     .shrink(shrink_factor, shrink_factor)
                     .embed(0, 0, 256, 256))            # pad to exactly 256²

            row, col = morton_row_col(idx, l)
            small_out = level_dir / f'{row}_{col}.jpg'
            small.jpegsave(str(small_out))

            # ---- 3.4 append <I … /> entry into dzc ------------------------- #
            dzc.write(f'  <I Id="{idx}" N="{idx}" IsPath="1" '
                      f'Source="{idx}.dzi">\n')
            dzc.write(f'    <Size Width="{width}" Height="{height}"/>\n')
            dzc.write('  </I>\n')

        dzc.write('</Items>\n</Collection>\n')

    # ----------------------------------------------------------------------- #
    #                    4. build upper pyramid levels                        #
    # ----------------------------------------------------------------------- #
    #
    # size = even number ≥ √n_items   (same calculation as original code)
    size = int(math.sqrt(n_items))
    if size * size < n_items:          # not a perfect square
        size <<= 1                     # multiply by two and make it even

    print (f'Building collection with {n_items} items, size={size}')  # debug output
    for level in range(max_level, 0, -1):
        upper = tiles_root / str(level)        # child level (already exists)
        current = tiles_root / str(level - 1)  # parent level (to create)
        mkdir(current)

        # iterate over 2×2 blocks of child tiles: (i-1,j-1) .. (i,j)
        for i in range(1, size+1, 2):
            for j in range(1, size+1, 2):
                def tile(r: int, c: int) -> Path:
                    return upper / f'{r}_{c}.jpg'

                # check which of the four children exist
                tl, tr = tile(i - 1, j - 1), tile(i, j - 1)
                bl, br = tile(i - 1, j),     tile(i, j)
                print (f'{i >> 1}_{j >> 1}')  # debug output
                #print (f'Processing tiles: {tl}, {tr}, {bl}, {br}')  # debug output
                # Print basename(dirname)+basename of each tile
                print (f'Processing tiles: {tl.name}, {tr.name}, '
                       f'{bl.name}, {br.name}')  # debug output
                print (f'Existing: {tl.exists()}, {tr.exists()}, '
                       f'{bl.exists()}, {br.exists()}')  # debug output
                # helper to load child tile at half resolution (shrink=2)
                def load(p: Path) -> pyvips.Image:
                    return pyvips.Image.new_from_file(str(p), shrink=2)

                parent: pyvips.Image | None = None
                if tl.exists() and tr.exists() and bl.exists() and br.exists():
                    parent = load(tl).join(load(tr), Direction.HORIZONTAL) \
                                       .join(load(bl).join(load(br),
                                                           Direction.HORIZONTAL),
                                             Direction.VERTICAL)

                elif tl.exists() and tr.exists() and bl.exists():
                    parent = load(tl).join(load(tr), Direction.HORIZONTAL) \
                                     .join(load(bl).embed(0, 0, 256, 128),
                                           Direction.VERTICAL)

                elif tl.exists() and tr.exists():
                    parent = load(tl).join(load(tr), Direction.HORIZONTAL) \
                                     .embed(0, 0, 256, 256)

                elif tl.exists():
                    parent = load(tl).embed(0, 0, 256, 256)

                # if at least one child existed -> write parent tile
                if parent is not None:
                    out_tile = current / f'{i >> 1}_{j >> 1}.jpg'
                    parent.jpegsave(str(out_tile))


# --------------------------------------------------------------------------- #
#                                   main                                      #
# --------------------------------------------------------------------------- #
def main(argv: Iterable[str] | None = None) -> None:
    """Entry point that mimics the 3-argument C++ program."""
    argv = list(argv or sys.argv[1:])
    if len(argv) != 3:
        sys.exit(f'Usage: {Path(sys.argv[0]).name} '
                 f'<input_dir> <output_dir> <output_name>')
    build_collection(*argv)


if __name__ == '__main__':
    main()