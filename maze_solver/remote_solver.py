from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import dataclass
from typing import List, Optional

import requests


BASE_URL = "https://maze-api-1gfd.onrender.com"

DIRECTIONS = {
    "N": (-1, 0),
    "S": (1, 0),
    "E": (0, 1),
    "W": (0, -1),
}


@dataclass(frozen=True)
class Cell:
    row: int
    col: int


@dataclass
class ParsedMaze:
    lines: List[str]
    rows: int
    cols: int
    start: Cell
    goal: Cell
    exit_direction: Optional[str]


def post_json(path, payload):
    url = BASE_URL + path
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()

    try:
        return response.json()
    except ValueError:
        return response.text


def get_text(path, params):
    url = BASE_URL + path
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()
    return response.text


def parse_ascii_maze(ascii_maze):
    raw_lines = ascii_maze.splitlines()
    if not raw_lines:
        raise ValueError("La API devolvio un laberinto ASCII vacio.")

    width = max(len(line) for line in raw_lines)
    lines = [line.ljust(width) for line in raw_lines]

    if len(lines) < 3 or width < 5:
        raise ValueError("El laberinto ASCII no tiene el formato esperado.")

    rows = (len(lines) - 1) // 2
    cols = (width - 1) // 4

    start = None
    goal = None

    for row in range(rows):
        for col in range(cols):
            label = _cell_label(lines, row, col)
            if label in {"@", "S", "P"}:
                start = Cell(row, col)
            if label in {"X", "G", "E"}:
                goal = Cell(row, col)

    if start is None:
        raise ValueError("No se encontro la celda inicial en el ASCII.")
    if goal is None:
        raise ValueError("No se encontro la salida en el ASCII.")

    exit_direction = _find_exit_direction(lines, rows, cols, goal)

    return ParsedMaze(
        lines=lines,
        rows=rows,
        cols=cols,
        start=start,
        goal=goal,
        exit_direction=exit_direction,
    )


def solve_with_bfs(parsed_maze):
    queue = deque([parsed_maze.start])
    parents = {
        parsed_maze.start: (None, None),
    }

    while queue:
        current = queue.popleft()

        if current == parsed_maze.goal:
            moves = _reconstruct_moves(parents, parsed_maze.start, parsed_maze.goal)
            if parsed_maze.exit_direction is not None:
                moves += parsed_maze.exit_direction
            return moves

        for direction, (row_delta, col_delta) in DIRECTIONS.items():
            neighbor = Cell(current.row + row_delta, current.col + col_delta)

            if not _in_bounds(parsed_maze, neighbor):
                continue
            if neighbor in parents:
                continue
            if not _can_move(parsed_maze.lines, current, direction):
                continue

            parents[neighbor] = (current, direction)
            queue.append(neighbor)

    raise RuntimeError("No se encontro una solucion para este laberinto.")


def run(size, solver_name):
    print(f"Iniciando partida size={size}, solver={solver_name!r}...")
    init_data = post_json("/init", {"size": size, "solver": solver_name})
    session_id = init_data["session_id"]

    print(f"Session: {session_id}")
    print("Descargando laberinto ASCII...")
    ascii_maze = get_text("/ascii", {"session": session_id})

    print("Parseando laberinto...")
    parsed_maze = parse_ascii_maze(ascii_maze)

    print("Resolviendo con BFS...")
    moves = solve_with_bfs(parsed_maze)
    print(f"Movimientos encontrados: {len(moves)}")

    print("Enviando solucion completa...")
    result = post_json("/moves", {"session": session_id, "moves": moves})

    print("Resultado final de la API:")
    if isinstance(result, (dict, list)):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result)


def main():
    parser = argparse.ArgumentParser(
        description="Solver local para la Maze API remota."
    )
    parser.add_argument("--size", type=int, required=True)
    parser.add_argument("--solver", required=True)
    args = parser.parse_args()

    run(args.size, args.solver)


def _cell_label(lines, row, col):
    line_index = 2 * row + 1
    col_index = 4 * col + 2
    return lines[line_index][col_index].strip()


def _in_bounds(parsed_maze, cell):
    return 0 <= cell.row < parsed_maze.rows and 0 <= cell.col < parsed_maze.cols


def _can_move(lines, cell, direction):
    row = cell.row
    col = cell.col

    if direction == "N":
        wall = lines[2 * row][4 * col + 1 : 4 * col + 4]
        return "-" not in wall
    if direction == "S":
        wall = lines[2 * row + 2][4 * col + 1 : 4 * col + 4]
        return "-" not in wall
    if direction == "W":
        wall = lines[2 * row + 1][4 * col]
        return wall != "|"
    if direction == "E":
        wall = lines[2 * row + 1][4 * col + 4]
        return wall != "|"

    raise ValueError(f"Direccion desconocida: {direction}")


def _find_exit_direction(lines, rows, cols, goal):
    possible_exits = []

    if goal.row == 0 and _can_move(lines, goal, "N"):
        possible_exits.append("N")
    if goal.row == rows - 1 and _can_move(lines, goal, "S"):
        possible_exits.append("S")
    if goal.col == 0 and _can_move(lines, goal, "W"):
        possible_exits.append("W")
    if goal.col == cols - 1 and _can_move(lines, goal, "E"):
        possible_exits.append("E")

    if not possible_exits:
        return None
    return possible_exits[0]


def _reconstruct_moves(parents, start, goal):
    moves_reversed = []
    current = goal

    while current != start:
        previous, direction = parents[current]
        if previous is None or direction is None:
            raise RuntimeError("Error interno al reconstruir la ruta.")

        moves_reversed.append(direction)
        current = previous

    moves_reversed.reverse()
    return "".join(moves_reversed)


if __name__ == "__main__":
    main()
