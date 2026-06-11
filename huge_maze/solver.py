"""Solvers for the lazy maze."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .core import Cell, Direction, cell_to_dict


class MazeSolveError(RuntimeError):
    """Raised when a solver cannot finish under the requested constraints."""


@dataclass(frozen=True)
class SolveResult:
    moves: list[Direction]
    path: list[Cell]
    expanded: int

    def to_dict(
        self,
        include_moves: bool = True,
        include_path: bool = True,
    ) -> dict[str, object]:
        data: dict[str, object] = {
            "move_count": len(self.moves),
            "path_length": len(self.path),
            "expanded": self.expanded,
        }
        if include_moves:
            data["moves"] = list(self.moves)
        if include_path:
            data["path"] = [cell_to_dict(cell) for cell in self.path]
        return data


def flood_fill_solve(
    maze,
    start: Cell | None = None,
    goal: Cell | None = None,
    max_expanded: int | None = None,
) -> SolveResult:
    """Solve with BFS, storing only visited cells.

    This is fine for small and medium mazes. On huge mazes, the visited set can
    still become too large, so max_expanded provides an explicit safety limit.
    """

    start = start or maze.start_cell
    goal = goal or maze.exit_cell
    maze.require_in_bounds(start)
    maze.require_in_bounds(goal)

    queue: deque[Cell] = deque([start])
    came_from: dict[Cell, tuple[Cell | None, Direction | None]] = {
        start: (None, None)
    }
    expanded = 0

    while queue:
        if max_expanded is not None and expanded >= max_expanded:
            raise MazeSolveError(
                f"flood_fill_solve exceeded max_expanded={max_expanded} "
                "before reaching the goal"
            )

        current = queue.popleft()
        expanded += 1
        if current == goal:
            return _reconstruct_path(came_from, start, goal, expanded)

        for direction, neighbor in maze.neighbors(current):
            if neighbor not in came_from:
                came_from[neighbor] = (current, direction)
                queue.append(neighbor)

    raise MazeSolveError("goal is not reachable from start")


def parent_chain_solve(maze, start: Cell | None = None) -> SolveResult:
    """Follow parent links from the start to the root/exit.

    This solver is fast because it uses the structure of LazyMaze: every cell
    has exactly one parent toward the root, so no search frontier is needed.
    """

    current = start or maze.start_cell
    maze.require_in_bounds(current)

    path = [current]
    moves: list[Direction] = []
    expanded = 1

    while current != maze.exit_cell:
        direction = maze.parent_direction(current)
        parent = maze.parent_cell(current)
        if direction is None or parent is None:
            raise MazeSolveError("parent chain ended before reaching the exit")
        moves.append(direction)
        path.append(parent)
        current = parent
        expanded += 1

    return SolveResult(moves=moves, path=path, expanded=expanded)


def _reconstruct_path(
    came_from: dict[Cell, tuple[Cell | None, Direction | None]],
    start: Cell,
    goal: Cell,
    expanded: int,
) -> SolveResult:
    path_reversed = [goal]
    moves_reversed: list[Direction] = []
    current = goal

    while current != start:
        previous, direction = came_from[current]
        if previous is None or direction is None:
            raise MazeSolveError("internal solver error while rebuilding path")
        path_reversed.append(previous)
        moves_reversed.append(direction)
        current = previous

    path_reversed.reverse()
    moves_reversed.reverse()
    return SolveResult(moves=moves_reversed, path=path_reversed, expanded=expanded)
