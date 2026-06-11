import unittest

from huge_maze.core import Cell, move
from huge_maze.lazy_maze import LazyMaze
from huge_maze.solver import MazeSolveError, flood_fill_solve, parent_chain_solve


class SolverTests(unittest.TestCase):
    def test_flood_fill_solves_small_maze(self) -> None:
        maze = LazyMaze(size=6, seed=123)

        result = flood_fill_solve(maze, max_expanded=500)

        self.assertEqual(result.path[0], maze.start_cell)
        self.assertEqual(result.path[-1], maze.exit_cell)
        self.assertGreater(result.expanded, 0)
        self._assert_valid_path(maze, result.path, result.moves)

    def test_flood_fill_stops_at_max_expanded(self) -> None:
        maze = LazyMaze(size=6, seed=123)

        with self.assertRaises(MazeSolveError):
            flood_fill_solve(maze, max_expanded=1)

    def test_parent_chain_reaches_exit(self) -> None:
        maze = LazyMaze(size=10, seed=456)

        result = parent_chain_solve(maze)

        self.assertEqual(result.path[0], maze.start_cell)
        self.assertEqual(result.path[-1], maze.exit_cell)
        self.assertEqual(len(result.path), len(result.moves) + 1)

    def test_parent_chain_path_is_valid_step_by_step(self) -> None:
        maze = LazyMaze(size=8, seed=999)

        result = parent_chain_solve(maze)

        self._assert_valid_path(maze, result.path, result.moves)

    def test_parent_chain_can_start_from_any_cell(self) -> None:
        maze = LazyMaze(size=10, seed=12)

        result = parent_chain_solve(maze, start=Cell(3, 7))

        self.assertEqual(result.path[0], Cell(3, 7))
        self.assertEqual(result.path[-1], maze.exit_cell)
        self._assert_valid_path(maze, result.path, result.moves)

    def _assert_valid_path(self, maze: LazyMaze, path, moves) -> None:
        self.assertEqual(len(path), len(moves) + 1)
        for current, direction, next_cell in zip(path, moves, path[1:]):
            self.assertEqual(move(current, direction), next_cell)
            self.assertEqual(maze.visible_directions(current)[direction], "path")


if __name__ == "__main__":
    unittest.main()
