"""Small shared types used by the lazy maze and solvers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["N", "S", "E", "W"]

DIRECTIONS: tuple[Direction, ...] = ("N", "S", "E", "W")
DELTAS: dict[Direction, tuple[int, int]] = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "W": (0, -1),
}
OPPOSITE: dict[Direction, Direction] = {
    "N": "S",
    "S": "N",
    "E": "W",
    "W": "E",
}


@dataclass(frozen=True, order=True)
class Cell:
    """A coordinate in the maze grid."""

    row: int
    col: int


def move(cell: Cell, direction: Direction) -> Cell:
    """Return the adjacent cell reached by moving one step."""

    row_delta, col_delta = DELTAS[direction]
    return Cell(cell.row + row_delta, cell.col + col_delta)


def direction_between(start: Cell, end: Cell) -> Direction:
    """Return the direction needed to move from start to an adjacent end cell."""

    row_delta = end.row - start.row
    col_delta = end.col - start.col
    for direction, delta in DELTAS.items():
        if delta == (row_delta, col_delta):
            return direction
    raise ValueError(f"{start!r} and {end!r} are not adjacent cells")


def cell_to_dict(cell: Cell) -> dict[str, int]:
    """Serialize a cell into JSON-friendly data."""

    return {"row": cell.row, "col": cell.col}
