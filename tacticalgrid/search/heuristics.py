"""Heurísticas admisibles para los algoritmos de búsqueda (A* y Beam).


Ambas devuelven una función `Position -> float` que estima el costo restante hasta
la meta sin sobrestimarlo:


- `crear_manhattan`: distancia Manhattan multiplicada por el costo mínimo de terreno.
  Cada paso mueve una celda y cuesta al menos `costo_minimo`, así que nunca
  sobrestima. Con costo mínimo 1 (caso del proyecto) es la distancia Manhattan pura.
- `crear_distancia_exacta` y `crear_distancia_exacta_multiple`: costo real de la
  mejor ruta hasta una o varias metas, calculado una sola vez con Dijkstra inverso
  desde las metas. Es el heurístico perfecto, así que A* expande los nodos
  estrictamente necesarios para la ruta óptima.
- `distancias_exactas`: núcleo compartido que devuelve el mapa completo de costos
  reales hacia las metas, usado por las heurísticas y por la utilidad de decisión.
"""


import heapq
import math
from typing import Callable, Iterable


from tacticalgrid.domain.board import Board
from tacticalgrid.domain.position import Position
from tacticalgrid.domain.rules import vecinos_ortogonales




def crear_manhattan(objetivo: Position, costo_minimo: float = 1) -> Callable[[Position], float]:
    """
    Purpose:
        Construir la heurística Manhattan escalada por el costo mínimo de terreno.


    Preconditions:
        `objetivo` es una Position; `costo_minimo` es un número positivo que no
        supera el costo de ninguna celda transitable.


    Postconditions:
        Devuelve h(p) = costo_minimo * (|Δfila| + |Δcolumna|), admisible y consistente.


    Complexity:
        O(1) por evaluación.

    """
    if not isinstance(objetivo, Position):
        raise ValueError("El objetivo debe ser una Position.")


    if type(costo_minimo) not in (int, float) or costo_minimo <= 0:
        raise ValueError("El costo mínimo debe ser un número positivo.")


    def heuristica(posicion: Position) -> float:
        distancia = abs(posicion.row - objetivo.row) + abs(posicion.column - objetivo.column)
        return costo_minimo * distancia


    return heuristica




def crear_manhattan_multiple(
    objetivos,
    costo_minimo: float = 1,
) -> Callable[[Position], float]:
    """
    Purpose:
        Construir una heurística Manhattan para varias metas: el mínimo de las
        distancias a cada objetivo, escalado por el costo mínimo de terreno.

    Preconditions:
        `objetivos` es un iterable no vacío de Position; `costo_minimo` es un
        número positivo que no supera el costo de ninguna celda transitable.

    Postconditions:
        Devuelve h(p) = costo_minimo * min_g(|Δfila| + |Δcolumna|) para g en
        objetivos. Es admisible y consistente, porque es mínimo de heurísticas
        admisibles y consistentes.

    Complexity:
        O(K) por evaluación, con K objetivos.
    """
    metas = tuple(objetivos)
    if not metas or any(not isinstance(g, Position) for g in metas):
        raise ValueError("Los objetivos deben ser un conjunto no vacío de Position.")

    if type(costo_minimo) not in (int, float) or costo_minimo <= 0:
        raise ValueError("El costo mínimo debe ser un número positivo.")

    def heuristica(posicion: Position) -> float:
        distancia = min(
            abs(posicion.row - g.row) + abs(posicion.column - g.column) for g in metas
        )
        return costo_minimo * distancia

    return heuristica


def distancias_exactas(
    tablero: Board,
    objetivos: Iterable[Position],
    bloqueadas: frozenset[Position] = frozenset(),
) -> dict[Position, float]:
    """
    Purpose:
        Calcular, con un Dijkstra inverso multi-origen, el costo real mínimo de
        cada celda hasta la meta más cercana del conjunto `objetivos`.

    Preconditions:
        `tablero` es un Board; `objetivos` es un iterable no vacío de Position
        transitables y no bloqueadas; `bloqueadas` son celdas que no se pueden
        atravesar.

    Postconditions:
        Devuelve un diccionario Position -> costo real mínimo hacia la meta más
        cercana. Las celdas sin ruta no aparecen. Entrar a una celda cuesta su
        costo de terreno, igual que en `ProblemaTablero`. No modifica entradas.

    Complexity:
        O(F*C*log(F*C)) una sola vez, F filas y C columnas.
    """
    metas = tuple(objetivos)
    if not metas:
        raise ValueError("Debe haber al menos un objetivo.")

    if any(not isinstance(p, Position) for p in bloqueadas):
        raise ValueError("Todas las celdas bloqueadas deben ser Position.")

    for objetivo in metas:
        if not isinstance(objetivo, Position):
            raise ValueError("Cada objetivo debe ser una Position.")

        if not tablero.is_inside(objetivo):
            raise ValueError(f"El objetivo {objetivo} está fuera del tablero.")

        if not tablero.is_walkable(objetivo):
            raise ValueError(f"El objetivo {objetivo} está sobre un obstáculo.")

        if objetivo in bloqueadas:
            raise ValueError(f"El objetivo {objetivo} está bloqueado.")

    distancias: dict[Position, float] = {meta: 0.0 for meta in metas}
    cola = [
        (0.0, desempate, meta)
        for desempate, meta in enumerate(metas)
    ]  # (distancia, desempate, celda)
    heapq.heapify(cola)
    desempate = len(metas)

    while cola:
        distancia, _, actual = heapq.heappop(cola)
        if distancia > distancias.get(actual, math.inf):
            continue

        # Para llegar a `actual` desde un vecino hay que pagar el costo de `actual`.
        costo_entrada = tablero.movement_cost(actual)
        for vecino in vecinos_ortogonales(actual):
            if not tablero.is_inside(vecino) or not tablero.is_walkable(vecino):
                continue
            if vecino in bloqueadas:
                continue
            nueva = distancia + costo_entrada
            if nueva < distancias.get(vecino, math.inf):
                distancias[vecino] = nueva
                heapq.heappush(cola, (nueva, desempate, vecino))
                desempate += 1

    return distancias


def crear_distancia_exacta(
    tablero: Board,
    objetivo: Position,
    bloqueadas: frozenset[Position] = frozenset(),
) -> Callable[[Position], float]:
    """
    Purpose:
        Construir la heurística de distancia exacta para una sola meta.

    Preconditions:
        `tablero` es un Board y `objetivo` es una celda transitable; `bloqueadas`
        son celdas que la búsqueda no puede atravesar.

    Postconditions:
        Devuelve h(p) = costo real mínimo de p a la meta, o infinito si no hay ruta.
        Entrar a una celda cuesta su costo de terreno, igual que en `ProblemaTablero`.

    Complexity:
        O(F*C*log(F*C)) una sola vez; O(1) por evaluación.

    """
    return crear_distancia_exacta_multiple(tablero, (objetivo,), bloqueadas)


def crear_distancia_exacta_multiple(
    tablero: Board,
    objetivos: Iterable[Position],
    bloqueadas: frozenset[Position] = frozenset(),
) -> Callable[[Position], float]:
    """
    Purpose:
        Construir la heurística de distancia exacta para varias metas: el costo
        real mínimo de llegar a cualquiera de ellas.

    Preconditions:
        `tablero` es un Board; `objetivos` es un iterable no vacío de Position
        transitables y no bloqueadas; `bloqueadas` son celdas no transitables.

    Postconditions:
        Devuelve h(p) = costo real mínimo de p a la meta más cercana, o infinito
        si no existe ruta. Es admisible y consistente.

    Complexity:
        O(F*C*log(F*C)) una sola vez; O(1) por evaluación.
    """
    distancias = distancias_exactas(tablero, objetivos, bloqueadas)

    def heuristica(posicion: Position) -> float:
        return distancias.get(posicion, math.inf)

    return heuristica
