"""A deterministic lazy maze that does not store the whole board."""

from __future__ import annotations

from dataclasses import dataclass

from .core import DIRECTIONS, Cell, Direction, move

ASCII_DISABLED_MESSAGE = (
    "Full ASCII rendering is disabled for huge mazes. Use /window instead."
)
MAX_WINDOW_CELLS = 10_000


class MazeTooLargeError(ValueError):
    """Raised when a caller asks for a full rendering of a huge maze."""


@dataclass(frozen=True)
class LazyMaze:
    """A coordinate-based maze generated only where it is queried.

    Each cell except the root at (0, 0) chooses exactly one parent to the North
    or West. A connection exists when either cell is the other's parent.
    """

    size: int
    seed: int = 0
    ascii_max_size: int = 40

    def __post_init__(self) -> None:
        if self.size < 1:
            raise ValueError("size must be at least 1")
        if self.ascii_max_size < 1:
            raise ValueError("ascii_max_size must be at least 1")

    @property
    def start_cell(self) -> Cell:
        return Cell(self.size - 1, self.size - 1)

    @property
    def exit_cell(self) -> Cell:
        return Cell(0, 0)

    @property
    def exit_direction(self) -> Direction:
        return "N"

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell.row < self.size and 0 <= cell.col < self.size

    def require_in_bounds(self, cell: Cell) -> None:
        if not self.in_bounds(cell):
            raise ValueError(f"cell {cell!r} is outside a {self.size}x{self.size} maze")

    def parent_direction(self, cell: Cell) -> Direction | None:
        """Return the direction from cell to its parent, or None for the root."""

        self.require_in_bounds(cell)
        if cell == self.exit_cell:
            return None
        if cell.row == 0:
            return "W"
        if cell.col == 0:
            return "N"
        return "N" if self._coin_flip(cell.row, cell.col) else "W"

    def parent_cell(self, cell: Cell) -> Cell | None:
        direction = self.parent_direction(cell)
        if direction is None:
            return None
        return move(cell, direction)

    def neighbors(self, cell: Cell) -> list[tuple[Direction, Cell]]:
        """Return reachable neighboring cells without looking at the full maze."""

        self.require_in_bounds(cell)
        result: list[tuple[Direction, Cell]] = []
        for direction in DIRECTIONS:
            neighbor = move(cell, direction)
            if self.in_bounds(neighbor) and self._connected(cell, neighbor):
                result.append((direction, neighbor))
        return result

    def visible_directions(self, cell: Cell) -> dict[str, str]:
        """Return wall/path/exit status for N, S, E and W around a cell."""

        self.require_in_bounds(cell)
        visible: dict[str, str] = {}
        for direction in DIRECTIONS:
            if cell == self.exit_cell and direction == self.exit_direction:
                visible[direction] = "exit"
                continue

            neighbor = move(cell, direction)
            if not self.in_bounds(neighbor):
                visible[direction] = "wall"
            elif self._connected(cell, neighbor):
                visible[direction] = "path"
            else:
                visible[direction] = "wall"
        return visible

    def render_window(self, center: Cell | None = None, radius: int = 5) -> str:
        """Render only a local window around center."""

        if radius < 0:
            raise ValueError("radius must be non-negative")
        center = center or self.start_cell
        self.require_in_bounds(center)

        row_min = max(0, center.row - radius)
        row_max = min(self.size - 1, center.row + radius)
        col_min = max(0, center.col - radius)
        col_max = min(self.size - 1, center.col + radius)
        cell_count = (row_max - row_min + 1) * (col_max - col_min + 1)
        if cell_count > MAX_WINDOW_CELLS:
            raise ValueError(
                f"window is too large: {cell_count} cells requested, "
                f"maximum is {MAX_WINDOW_CELLS}"
            )
        return self._render_cells(row_min, row_max, col_min, col_max, marker=center)

    def render_ascii(self, marker: Cell | None = None) -> str:
        """Render the full maze only when it is small enough to be useful."""

        if self.size > self.ascii_max_size:
            raise MazeTooLargeError(ASCII_DISABLED_MESSAGE)
        marker = marker or self.start_cell
        self.require_in_bounds(marker)
        return self._render_cells(0, self.size - 1, 0, self.size - 1, marker=marker)

    def _connected(self, first: Cell, second: Cell) -> bool:
        if abs(first.row - second.row) + abs(first.col - second.col) != 1:
            return False
        return self.parent_cell(first) == second or self.parent_cell(second) == first

    def _coin_flip(self, row: int, col: int) -> bool:
        """Stable pseudo-random bit based on coordinates and seed."""

        mask = (1 << 64) - 1
        value = (
            row * 0x9E3779B185EBCA87
            + col * 0xC2B2AE3D27D4EB4F
            + (self.seed & mask) * 0x165667B19E3779F9
        ) & mask
        value ^= value >> 30
        value = (value * 0xBF58476D1CE4E5B9) & mask
        value ^= value >> 27
        value = (value * 0x94D049BB133111EB) & mask
        value ^= value >> 31
        return bool(value & 1)

    def _render_cells(
        self,
        row_min: int,
        row_max: int,
        col_min: int,
        col_max: int,
        marker: Cell,
    ) -> str:
        lines: list[str] = []
        for row in range(row_min, row_max + 1):
            top_parts: list[str] = []
            for col in range(col_min, col_max + 1):
                top_parts.append("+" + self._horizontal(Cell(row, col), "N"))
            lines.append("".join(top_parts) + "+")

            middle_parts: list[str] = []
            for col in range(col_min, col_max + 1):
                cell = Cell(row, col)
                middle_parts.append(self._vertical(cell, "W") + self._cell_label(cell, marker))
            last_cell = Cell(row, col_max)
            lines.append("".join(middle_parts) + self._vertical(last_cell, "E"))

        bottom_parts: list[str] = []
        for col in range(col_min, col_max + 1):
            bottom_parts.append("+" + self._horizontal(Cell(row_max, col), "S"))
        lines.append("".join(bottom_parts) + "+")
        return "\n".join(lines)

    def _horizontal(self, cell: Cell, direction: Direction) -> str:
        state = self.visible_directions(cell)[direction]
        if state == "path":
            return "   "
        if state == "exit":
            return " E "
        return "---"

    def _vertical(self, cell: Cell, direction: Direction) -> str:
        state = self.visible_directions(cell)[direction]
        if state == "path":
            return " "
        if state == "exit":
            return "E"
        return "|"

    def _cell_label(self, cell: Cell, marker: Cell) -> str:
        if cell == marker:
            return " @ "
        if cell == self.start_cell:
            return " S "
        if cell == self.exit_cell:
            return " X "
        return "   "
