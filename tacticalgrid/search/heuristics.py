"""Heurísticas admisibles para los algoritmos de búsqueda (A* y Beam).


Ambas devuelven una función `Position -> float` que estima el costo restante hasta
la meta sin sobrestimarlo:


- `crear_manhattan`: distancia Manhattan multiplicada por el costo mínimo de terreno.
  Cada paso mueve una celda y cuesta al menos `costo_minimo`, así que nunca
  sobrestima. Con costo mínimo 1 (caso del proyecto) es la distancia Manhattan pura.
- `crear_distancia_exacta`: costo real de la mejor ruta hasta la meta, calculado una
  sola vez con Dijkstra desde la meta. Es el heurístico perfecto, así que A* expande
  los nodos estrictamente necesarios para la ruta óptima.
"""


import heapq
import math
from typing import Callable


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




def crear_distancia_exacta(
    tablero: Board,
    objetivo: Position,
    bloqueadas: frozenset[Position] = frozenset(),
) -> Callable[[Position], float]:
    """
    Purpose:
        Construir la heurística de distancia exacta precalculando Dijkstra desde la meta.


    Preconditions:
        `tablero` es un Board y `objetivo` es una celda transitable; `bloqueadas`
        son celdas que la búsqueda no puede atravesar.


    Postconditions:
        Devuelve h(p) = costo real mínimo de p a la meta, o infinito si no hay ruta.
        Entrar a una celda cuesta su costo de terreno, igual que en `ProblemaTablero`.


    Complexity:
        O(F*C*log(F*C)) una sola vez; O(1) por evaluación.


    """
    if any(not isinstance(p, Position) for p in bloqueadas):
        raise ValueError("Todas las celdas bloqueadas deben ser Position.")


    if not tablero.is_inside(objetivo):
        raise ValueError("El objetivo está fuera del tablero.")


    if not tablero.is_walkable(objetivo):
        raise ValueError("El objetivo está sobre un obstáculo.")


    if objetivo in bloqueadas:
        raise ValueError("El objetivo está bloqueado.")


    distancias: dict[Position, float] = {objetivo: 0.0}
    cola = [(0.0, 0, objetivo)]  # (distancia, desempate, celda)
    desempate = 1


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


    def heuristica(posicion: Position) -> float:
        return distancias.get(posicion, math.inf)


    return heuristica
