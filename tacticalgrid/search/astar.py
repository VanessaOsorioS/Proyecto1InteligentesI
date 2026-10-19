"""Algoritmo A* sobre un `Problema` con heurística admisible.


Prioriza los nodos por f(n) = g(n) + h(n), donde g es el costo real acumulado y h
la estimación hasta la meta. Con una heurística admisible y consistente, el primer
nodo meta expandido tiene el costo mínimo.
"""


import heapq
import math
import time
from typing import Callable


from tacticalgrid.domain.position import Position
from tacticalgrid.metrics.search_metrics import MetricasBusqueda
from tacticalgrid.search.problem import Problema, ResultadoBusqueda




def buscar(
    problema: Problema,
    heuristica: Callable[[Position], float],
) -> ResultadoBusqueda:
    """
    Purpose:
        Encontrar una ruta de costo mínimo desde el inicio hasta la meta con A*.


    Preconditions:
        `problema` cumple la interfaz `Problema`; `heuristica` es admisible y
        consistente con los costos de transición del problema.


    Postconditions:
        Devuelve ResultadoBusqueda con el camino óptimo y sus métricas si existe ruta.
        Si no existe, devuelve exito=False, camino vacío y costo infinito.
        Cada llamada es independiente; no guarda estado entre búsquedas.
        `generados` cuenta los nodos insertados en la frontera.


    Complexity:
        O(b^d) en el peor caso con factor de ramificación b y profundidad d;
        O(E log V) con el heap binario, con V nodos y E transiciones.


    """
    inicio_tiempo = time.perf_counter()


    h_inicio = heuristica(problema.inicio)
    frontera = [(h_inicio, 0, 0.0, problema.inicio)]  # (f, desempate, g, nodo)
    mejor_g = {problema.inicio: 0.0}
    padre: dict[Position, Position] = {}
    cerrados: set[Position] = set()
    orden: list[Position] = []
    generados = 0
    frontera_maxima = 1
    desempate = 1


    while frontera:
        _, _, g, nodo = heapq.heappop(frontera)


        # Entrada obsoleta: el nodo ya se expandió con un costo igual o menor.
        if nodo in cerrados:
            continue


        cerrados.add(nodo)
        orden.append(nodo)


        if problema.es_objetivo(nodo):
            camino = _reconstruir_camino(padre, problema.inicio, nodo)
            metricas = MetricasBusqueda(
                generados=generados,
                expandidos=len(orden),
                frontera_maxima=frontera_maxima,
                tiempo_segundos=time.perf_counter() - inicio_tiempo,
                orden_expansion=tuple(orden),
            )
            return ResultadoBusqueda(camino, g, True, metricas)


        for vecino, costo in problema.sucesores(nodo):
            nuevo_g = g + costo
            if nuevo_g >= mejor_g.get(vecino, math.inf):
                continue


            h = heuristica(vecino)
            if h == math.inf:
                # Sin ruta hacia la meta desde este vecino: no vale la pena insertarlo.
                continue


            mejor_g[vecino] = nuevo_g
            padre[vecino] = nodo
            heapq.heappush(frontera, (nuevo_g + h, desempate, nuevo_g, vecino))
            desempate += 1
            generados += 1
            frontera_maxima = max(frontera_maxima, len(frontera))


    metricas = MetricasBusqueda(
        generados=generados,
        expandidos=len(orden),
        frontera_maxima=frontera_maxima,
        tiempo_segundos=time.perf_counter() - inicio_tiempo,
        orden_expansion=tuple(orden),
    )
    return ResultadoBusqueda((), math.inf, False, metricas)




def _reconstruir_camino(
    padre: dict[Position, Position],
    inicio: Position,
    meta: Position,
) -> tuple[Position, ...]:
    """
    Purpose:
        Recorrer los punteros de padre desde la meta hasta el inicio.


    Preconditions:
        `meta` es alcanzable desde `inicio` según el diccionario `padre`.


    Postconditions:
        Devuelve la secuencia de posiciones de inicio a meta, ambas incluidas.


    Complexity:
        O(L), con L longitud del camino.


    """
    camino = [meta]
    actual = meta
    while actual != inicio:
        actual = padre[actual]
        camino.append(actual)
    camino.reverse()
    return tuple(camino)


