# Maze Solver Remoto

Este proyecto contiene un solver local en Python para conectarse a la Maze API remota, iniciar una partida, descargar el laberinto en ASCII, resolverlo con BFS y enviar la ruta completa al servidor.

El solver vive en tu computador. No se sube a Render y no modifica el servidor remoto; solo se comunica con la API usando `requests`.

## Instalar dependencias

```bash
cd maze_solver
python -m pip install -r requirements.txt
```

## Ejecutar

Con size 1000:

```bash
python remote_solver.py --size 1000 --solver eduardo-test
```

Con size 10000:

```bash
python remote_solver.py --size 10000 --solver eduardo-test
```

Con size 100000:

```bash
python remote_solver.py --size 100000 --solver eduardo-test
```

Con size 1000000:

```bash
python remote_solver.py --size 1000000 --solver eduardo-test
```

## Que hace

1. Llama a `POST /init` con el tamano y el nombre del solver.
2. Lee el `session_id`.
3. Descarga el laberinto con `GET /ascii?session=...`.
4. Parsea el ASCII para encontrar inicio, salida y paredes.
5. Resuelve el laberinto con BFS usando `collections.deque`.
6. Envia la solucion completa con `POST /moves`.
7. Imprime el resultado final de la API.
