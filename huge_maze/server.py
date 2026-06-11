"""Small standard-library HTTP API for the lazy maze."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import RLock
from typing import cast
from urllib.parse import parse_qs, urlparse

from .core import DIRECTIONS, Direction, cell_to_dict, move
from .lazy_maze import ASCII_DISABLED_MESSAGE, LazyMaze, MazeTooLargeError
from .solver import parent_chain_solve


class MazeGame:
    """Mutable player state on top of an immutable LazyMaze."""

    def __init__(self, maze: LazyMaze) -> None:
        self.maze = maze
        self.position = maze.start_cell
        self.won = False
        self._lock = RLock()

    def state(self) -> dict[str, object]:
        with self._lock:
            return {
                "size": self.maze.size,
                "seed": self.maze.seed,
                "position": cell_to_dict(self.position),
                "start": cell_to_dict(self.maze.start_cell),
                "exit": cell_to_dict(self.maze.exit_cell),
                "exit_direction": self.maze.exit_direction,
                "visible": self.maze.visible_directions(self.position),
                "won": self.won,
            }

    def move(self, direction: str) -> dict[str, object]:
        with self._lock:
            normalized = direction.upper()
            if normalized not in DIRECTIONS:
                return {
                    "moved": False,
                    "error": f"direction must be one of {', '.join(DIRECTIONS)}",
                    "state": self.state(),
                }

            typed_direction = cast(Direction, normalized)
            visible = self.maze.visible_directions(self.position)
            status = visible[typed_direction]
            if status == "path":
                self.position = move(self.position, typed_direction)
                return {"moved": True, "state": self.state()}
            if status == "exit":
                self.won = True
                return {
                    "moved": True,
                    "message": "You reached the exit.",
                    "state": self.state(),
                }
            return {
                "moved": False,
                "blocked_by": "wall",
                "state": self.state(),
            }

    def reset(self) -> dict[str, object]:
        with self._lock:
            self.position = self.maze.start_cell
            self.won = False
            return self.state()

    def window(self, radius: int) -> str:
        with self._lock:
            return self.maze.render_window(self.position, radius=radius)

    def ascii(self) -> str:
        with self._lock:
            return self.maze.render_ascii(self.position)


def create_handler(game: MazeGame) -> type[BaseHTTPRequestHandler]:
    class HugeMazeHandler(BaseHTTPRequestHandler):
        server_version = "HugeMazeHTTP/0.1"

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)

            if parsed.path == "/state":
                self._send_json(game.state())
                return
            if parsed.path == "/move":
                direction = self._first(query, "direction")
                if direction is None:
                    self._send_json({"error": "missing direction"}, status=400)
                    return
                response = game.move(direction)
                status = 400 if "error" in response else 200
                self._send_json(response, status=status)
                return
            if parsed.path == "/reset":
                self._send_json(game.reset())
                return
            if parsed.path == "/window":
                radius = self._int_query(query, "radius", default=5)
                if radius is None:
                    self._send_json({"error": "radius must be an integer"}, status=400)
                    return
                try:
                    self._send_text(game.window(radius))
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=400)
                return
            if parsed.path == "/ascii":
                try:
                    self._send_text(game.ascii())
                except MazeTooLargeError:
                    self._send_text(ASCII_DISABLED_MESSAGE, status=413)
                return
            if parsed.path == "/solve":
                self._send_json(self._solve_payload(query))
                return

            self._send_json({"error": "not found"}, status=404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)

            if parsed.path == "/move":
                body = self._body_data()
                direction = body.get("direction") or self._first(query, "direction")
                if direction is None:
                    self._send_json({"error": "missing direction"}, status=400)
                    return
                response = game.move(str(direction))
                status = 400 if "error" in response else 200
                self._send_json(response, status=status)
                return
            if parsed.path == "/reset":
                self._send_json(game.reset())
                return

            self._send_json({"error": "not found"}, status=404)

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_json(self, payload: object, status: int = 200) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, text: str, status: int = 200) -> None:
            body = text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body_data(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            if not raw:
                return {}

            content_type = self.headers.get("Content-Type", "")
            if "application/json" in content_type:
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    return {}
                return data if isinstance(data, dict) else {}

            parsed = parse_qs(raw)
            return {key: values[0] for key, values in parsed.items() if values}

        def _solve_payload(self, query: dict[str, list[str]]) -> dict[str, object]:
            result = parent_chain_solve(game.maze)
            limit = self._int_query(query, "limit", default=5000)
            if limit is None:
                limit = 5000
            include_moves = self._include_field(
                self._first(query, "include_moves"), len(result.moves), limit
            )
            include_path = self._include_field(
                self._first(query, "include_path"), len(result.path), limit
            )

            payload = result.to_dict(
                include_moves=include_moves,
                include_path=include_path,
            )
            payload["start"] = cell_to_dict(game.maze.start_cell)
            payload["exit"] = cell_to_dict(game.maze.exit_cell)
            payload["exit_direction"] = game.maze.exit_direction
            payload["moves_omitted"] = not include_moves
            payload["path_omitted"] = not include_path
            return payload

        def _include_field(self, value: str | None, length: int, limit: int) -> bool:
            if value is None or value == "auto":
                return length <= limit
            return value.lower() in {"1", "true", "yes", "y"}

        def _int_query(
            self,
            query: dict[str, list[str]],
            name: str,
            default: int,
        ) -> int | None:
            raw = self._first(query, name)
            if raw is None:
                return default
            try:
                return int(raw)
            except ValueError:
                return None

        def _first(self, query: dict[str, list[str]], name: str) -> str | None:
            values = query.get(name)
            return values[0] if values else None

    return HugeMazeHandler


def make_server(
    size: int,
    seed: int,
    host: str = "127.0.0.1",
    port: int = 8000,
    ascii_max_size: int = 40,
) -> ThreadingHTTPServer:
    maze = LazyMaze(size=size, seed=seed, ascii_max_size=ascii_max_size)
    game = MazeGame(maze)
    handler = create_handler(game)
    return ThreadingHTTPServer((host, port), handler)


def run_server(
    size: int,
    seed: int,
    host: str = "127.0.0.1",
    port: int = 8000,
    ascii_max_size: int = 40,
) -> None:
    server = make_server(size, seed, host=host, port=port, ascii_max_size=ascii_max_size)
    address, actual_port = server.server_address
    print(f"Serving huge maze at http://{address}:{actual_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server")
    finally:
        server.server_close()
