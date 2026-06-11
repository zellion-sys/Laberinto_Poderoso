import json
import threading
import unittest
import urllib.error
import urllib.request

from huge_maze.lazy_maze import ASCII_DISABLED_MESSAGE
from huge_maze.server import make_server


class ApiTests(unittest.TestCase):
    def test_window_returns_small_text_for_huge_maze(self) -> None:
        server, base_url, thread = self._start_server(size=10**6, seed=123)
        try:
            body = self._get_text(base_url + "/window?radius=5")

            self.assertIn("@", body)
            self.assertLess(len(body), 1200)
        finally:
            self._stop_server(server, thread)

    def test_ascii_is_blocked_for_huge_maze(self) -> None:
        server, base_url, thread = self._start_server(size=10**6, seed=123)
        try:
            with self.assertRaises(urllib.error.HTTPError) as context:
                urllib.request.urlopen(base_url + "/ascii", timeout=5)

            self.assertEqual(context.exception.code, 413)
            self.assertEqual(context.exception.read().decode("utf-8"), ASCII_DISABLED_MESSAGE)
            context.exception.close()
        finally:
            self._stop_server(server, thread)

    def test_ascii_works_for_small_maze(self) -> None:
        server, base_url, thread = self._start_server(size=4, seed=1)
        try:
            body = self._get_text(base_url + "/ascii")

            self.assertIn("@", body)
            self.assertIn("+", body)
        finally:
            self._stop_server(server, thread)

    def test_state_and_move_endpoints_return_json(self) -> None:
        server, base_url, thread = self._start_server(size=8, seed=5)
        try:
            state = self._get_json(base_url + "/state")
            direction = next(
                key for key, value in state["visible"].items() if value == "path"
            )
            moved = self._get_json(base_url + f"/move?direction={direction}")

            self.assertTrue(moved["moved"])
            self.assertIn("state", moved)
        finally:
            self._stop_server(server, thread)

    def test_solve_endpoint_reports_parent_chain_solution(self) -> None:
        server, base_url, thread = self._start_server(size=5, seed=2)
        try:
            solution = self._get_json(base_url + "/solve")

            self.assertEqual(solution["path"][0], {"row": 4, "col": 4})
            self.assertEqual(solution["path"][-1], {"row": 0, "col": 0})
            self.assertEqual(solution["path_length"], solution["move_count"] + 1)
        finally:
            self._stop_server(server, thread)

    def _start_server(self, size: int, seed: int):
        server = make_server(size=size, seed=seed, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        return server, f"http://{host}:{port}", thread

    def _stop_server(self, server, thread) -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    def _get_text(self, url: str) -> str:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.read().decode("utf-8")

    def _get_json(self, url: str):
        return json.loads(self._get_text(url))


if __name__ == "__main__":
    unittest.main()
