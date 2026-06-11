"""Command line entry points for huge_maze."""

from __future__ import annotations

import argparse

from .core import cell_to_dict
from .lazy_maze import LazyMaze
from .server import run_server
from .solver import parent_chain_solve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m huge_maze.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="start the HTTP API")
    _add_maze_args(serve)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--ascii-max-size", type=int, default=40)

    solve = subparsers.add_parser("solve", help="solve using the parent chain")
    _add_maze_args(solve)
    solve.add_argument(
        "--show-moves",
        action="store_true",
        help="print every move; this can be very large",
    )

    window = subparsers.add_parser("window", help="render a local maze window")
    _add_maze_args(window)
    window.add_argument("--radius", type=int, default=5)
    window.add_argument("--row", type=int)
    window.add_argument("--col", type=int)

    args = parser.parse_args(argv)

    if args.command == "serve":
        run_server(
            size=args.size,
            seed=args.seed,
            host=args.host,
            port=args.port,
            ascii_max_size=args.ascii_max_size,
        )
        return 0

    maze = LazyMaze(size=args.size, seed=args.seed)

    if args.command == "solve":
        result = parent_chain_solve(maze)
        print(f"size: {maze.size}x{maze.size}")
        print(f"seed: {maze.seed}")
        print(f"start: {cell_to_dict(maze.start_cell)}")
        print(f"exit: {cell_to_dict(maze.exit_cell)} via {maze.exit_direction}")
        print(f"moves: {len(result.moves)}")
        print(f"path cells: {len(result.path)}")
        print(f"expanded: {result.expanded}")
        if args.show_moves:
            print("".join(result.moves))
        else:
            preview = "".join(result.moves[:80])
            suffix = "..." if len(result.moves) > 80 else ""
            print(f"move preview: {preview}{suffix}")
        return 0

    if args.command == "window":
        center = maze.start_cell
        if args.row is not None or args.col is not None:
            if args.row is None or args.col is None:
                parser.error("--row and --col must be used together")
            from .core import Cell

            center = Cell(args.row, args.col)
        print(maze.render_window(center=center, radius=args.radius))
        return 0

    parser.error("unknown command")
    return 2


def _add_maze_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--seed", type=int, default=0)


if __name__ == "__main__":
    raise SystemExit(main())
