# Huge Lazy Maze

Este repositorio implementa un maze inspirado en `radix1001/linear_optimization/maze_api`, pero con un enfoque pensado para explicar y probar por que un tablero enorme no debe materializarse completo.

La idea principal es que un maze de `10**6 x 10**6` tiene `10**12` celdas. Guardar una matriz, un diccionario con todas las celdas, todas las paredes o un ASCII completo seria inviable para una computadora normal. En vez de eso, este proyecto calcula localmente lo que necesita.

## Que hacia el enfoque original

El enfoque original tenia un `server.py` con una clase de maze, endpoints como `/state`, `/move`, `/reset` y `/ascii`, y un `solver.py` que parseaba el ASCII completo para resolver con BFS usando `deque`.

Eso esta bien para mazes chicos: el ASCII cabe en memoria, se puede leer entero y BFS puede visitar una parte importante del tablero. El problema aparece cuando el tablero crece. Para `10**12` celdas, incluso una marca por celda ya seria demasiado, y un BFS completo puede necesitar guardar millones o billones de visitados en el peor caso.

## Como escala esta version

`LazyMaze` no crea una matriz `size x size` y no guarda un diccionario global de celdas. Cada celda se representa como:

```python
Cell(row: int, col: int)
```

El generador usa una regla local y deterministica:

- La salida esta en `(0, 0)`.
- Cada celda, salvo `(0, 0)`, elige un padre al Norte o al Oeste.
- La eleccion se calcula con un hash estable de `(row, col, seed)`.
- Dos celdas estan conectadas si una es padre de la otra.

Con esto, consultar las paredes de una celda solo requiere mirar esa celda y sus vecinos inmediatos. No hay DFS global ni recursive backtracker sobre todo el tablero.

Esta estrategia tiene un sesgo estructural: los caminos tienden hacia Norte/Oeste porque el maze es un arbol orientado hacia la salida. No pretende ser un maze aleatorio perfecto como uno generado por DFS global. Se eligio porque es simple, didactico y permite tamaños gigantes sin almacenar `10**12` celdas.

## Solvers

Hay dos formas de resolver:

`flood_fill_solve`

Usa BFS con `collections.deque`. Guarda solo las celdas visitadas, no el tablero completo. Sirve para mazes pequeños o medianos. Aun asi, BFS puede crecer demasiado en mazes enormes, por eso acepta `max_expanded` y falla con un error claro si supera ese limite.

`parent_chain_solve`

Aprovecha la estructura de `LazyMaze`: como cada celda tiene un padre hacia la raiz `(0, 0)`, basta seguir padres desde el inicio hasta la salida. Para un maze de `10**6 x 10**6`, el camino desde la esquina inferior derecha tiene alrededor de dos millones de pasos, no `10**12`.

## API HTTP

Levantar el servidor:

```bash
python -m huge_maze.cli serve --size 1000000 --seed 123
```

Endpoints:

- `GET /state`
- `GET /move?direction=N`
- `POST /move` con JSON como `{"direction": "N"}`
- `POST /reset`
- `GET /window?radius=5`
- `GET /solve`
- `GET /ascii`

`/ascii` solo esta habilitado para mazes chicos. En mazes grandes devuelve HTTP 413:

```text
Full ASCII rendering is disabled for huge mazes. Use /window instead.
```

Para inspeccionar mazes grandes, usa `/window`. Por ejemplo, `radius=5` muestra como maximo una ventana de `11 x 11` celdas alrededor de la posicion actual.

Las ventanas tambien tienen un limite de seguridad: no se renderizan mas de 10.000 celdas en una sola respuesta.

## CLI

Resolver con la cadena de padres:

```bash
python -m huge_maze.cli solve --size 1000000 --seed 123
```

Mostrar una ventana local:

```bash
python -m huge_maze.cli window --size 1000000 --seed 123 --radius 5
```

Servidor HTTP:

```bash
python -m huge_maze.cli serve --size 1000000 --seed 123
```

## Tests

El proyecto usa solo librerias estandar de Python. Corre las pruebas con:

```bash
python -m unittest discover
```

Las pruebas cubren:

- `LazyMaze` no guarda una estructura `n*n`.
- `visible_directions` siempre reporta `N`, `S`, `E`, `W`.
- BFS funciona en mazes pequeños.
- La solucion por cadena de padres llega a la salida.
- El camino devuelto es valido paso a paso.
- `/window` responde con texto pequeño para `10**6 x 10**6`.
- `/ascii` funciona en pequeño y se bloquea en grande.

## Limitaciones

- El maze lazy tiene sesgo Norte/Oeste.
- `parent_chain_solve` devuelve listas de movimientos y celdas; para tamaños mucho mas grandes que `10**6`, convendria agregar una version que emita el camino como stream.
- `/solve` omite `moves` y `path` automaticamente si superan el limite de respuesta, aunque sigue reportando longitudes. Puedes ajustar esto con `include_moves`, `include_path` y `limit`.
