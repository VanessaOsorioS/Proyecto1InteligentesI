
"""Búsqueda en anchura (BFS) para problemas de navegación."""

from collections import deque
from time import perf_counter

from tacticalgrid.domain.position import Position
from tacticalgrid.search.problem import Problema, ResultadoBusqueda
from tacticalgrid.metrics.search_metrics import MetricasBusqueda


def reconstruir_camino(
    padres: dict[Position, Position | None],
    objetivo: Position,
) -> tuple[Position, ...]:
    """Reconstruye la ruta desde el inicio hasta el objetivo."""
    camino = []
    actual = objetivo

    while actual is not None:
        camino.append(actual)
        actual = padres[actual]

    camino.reverse()
    return tuple(camino)


def bfs(problema: Problema) -> ResultadoBusqueda:
    """
    Purpose:
        Encontrar un camino con el menor número de movimientos
        desde el inicio hasta una posición objetivo.

    Preconditions:
        El problema tiene un inicio válido y sucesores con
        costos de transición no negativos.

    Postconditions:
        Devuelve el camino, su costo y las métricas de búsqueda.
        Si no existe ruta, devuelve exito=False.

    Complexity:
        Tiempo O(V + E), espacio O(V + E) considerando
        la estructura de sucesores y el almacenamiento
        del árbol de búsqueda.


    Student validation:
        Pendiente de ejecución y validación del equipo.
    """

    inicio_tiempo = perf_counter()

    cola = deque([problema.inicio])
    visitados = {problema.inicio}

    padres: dict[Position, Position | None] = {
        problema.inicio: None
    }

    costos_acumulados = {problema.inicio: 0.0}

    generados = 1
    frontera_maxima = 1
    orden_expansion = []

    while cola:
        actual = cola.popleft()

        # Si encontramos la meta, reconstruimos la ruta.
        if problema.es_objetivo(actual):
            camino = reconstruir_camino(padres, actual)

            metricas = MetricasBusqueda(
                generados=generados,
                expandidos=len(orden_expansion),
                frontera_maxima=frontera_maxima,
                tiempo_segundos=perf_counter() - inicio_tiempo,
                orden_expansion=tuple(orden_expansion),
            )

            return ResultadoBusqueda(
                camino=camino,
                costo=costos_acumulados[actual],
                exito=True,
                metricas=metricas,
            )

        # Expandir el nodo actual.
        orden_expansion.append(actual)

        for vecino, costo in problema.sucesores(actual):
            if vecino in visitados:
                continue

            visitados.add(vecino)
            padres[vecino] = actual

            costos_acumulados[vecino] = (
                costos_acumulados[actual] + costo
            )

            cola.append(vecino)
            generados += 1

        frontera_maxima = max(
            frontera_maxima,
            len(cola),
        )

    # No existe una ruta hacia la meta.
    metricas = MetricasBusqueda(
        generados=generados,
        expandidos=len(orden_expansion),
        frontera_maxima=frontera_maxima,
        tiempo_segundos=perf_counter() - inicio_tiempo,
        orden_expansion=tuple(orden_expansion),
    )

    return ResultadoBusqueda(
        camino=(),
        costo=float("inf"),
        exito=False,
        metricas=metricas,
    )
