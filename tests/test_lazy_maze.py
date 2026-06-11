import unittest

from huge_maze.core import DIRECTIONS, Cell
from huge_maze.lazy_maze import ASCII_DISABLED_MESSAGE, LazyMaze, MazeTooLargeError


class LazyMazeTests(unittest.TestCase):
    def test_large_maze_does_not_store_grid(self) -> None:
        maze = LazyMaze(size=10**6, seed=123)

        self.assertNotIn("cells", vars(maze))
        self.assertNotIn("grid", vars(maze))
        self.assertLessEqual(len(vars(maze)), 3)
        self.assertEqual(set(maze.visible_directions(Cell(999_999, 999_999))), set(DIRECTIONS))

    def test_visible_directions_always_reports_four_compass_directions(self) -> None:
        maze = LazyMaze(size=10, seed=7)

        visible = maze.visible_directions(Cell(4, 4))

        self.assertEqual(set(visible), set(DIRECTIONS))
        self.assertLessEqual(set(visible.values()), {"wall", "path", "exit"})

    def test_full_ascii_only_for_small_mazes(self) -> None:
        small = LazyMaze(size=4, seed=1)
        huge = LazyMaze(size=100, seed=1, ascii_max_size=10)

        self.assertIn("@", small.render_ascii())
        with self.assertRaises(MazeTooLargeError) as context:
            huge.render_ascii()
        self.assertEqual(str(context.exception), ASCII_DISABLED_MESSAGE)


if __name__ == "__main__":
    unittest.main()
