
"""Búsqueda en profundidad (DFS) para TacticalGrid."""

from time import perf_counter

from tacticalgrid.domain.position import Position
from tacticalgrid.metrics.search_metrics import MetricasBusqueda
from tacticalgrid.search.problem import Problema, ResultadoBusqueda


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


def dfs(problema: Problema) -> ResultadoBusqueda:
    """
    Purpose:
        Buscar una ruta desde el inicio hasta la meta utilizando
        exploración en profundidad.

    Preconditions:
        El problema tiene un inicio válido, estados identificables
        mediante Position y un número finito de posiciones alcanzables.

    Postconditions:
        Devuelve una ruta si existe, con su costo y métricas.
        Si no existe ruta, devuelve exito=False.
        El estado del problema no se modifica.

    Complexity:
        Tiempo O(V + E), espacio O(V) para el recorrido de un
        grafo finito con conjunto de visitados.

    Student validation:
        Pendiente de ejecución y comprobación por el equipo.
    """

    inicio_tiempo = perf_counter()

    pila = [problema.inicio]
    visitados = {problema.inicio}

    padres: dict[Position, Position | None] = {
        problema.inicio: None
    }

    costos_acumulados = {
        problema.inicio: 0.0
    }

    generados = 1
    frontera_maxima = 1
    orden_expansion = []

    while pila:
        actual = pila.pop()

        # Comprobar si llegamos al objetivo.
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

        # El nodo se expande únicamente si no es la meta.
        orden_expansion.append(actual)

        # La pila es LIFO. Invertimos los sucesores
        # para respetar el orden definido en ProblemaTablero.
        sucesores = tuple(problema.sucesores(actual))

        for vecino, costo in reversed(sucesores):
            if vecino in visitados:
                continue

            visitados.add(vecino)

            padres[vecino] = actual

            costos_acumulados[vecino] = (
                costos_acumulados[actual] + costo
            )

            pila.append(vecino)
            generados += 1

        frontera_maxima = max(
            frontera_maxima,
            len(pila)
        )

    # No se encontró ninguna ruta.
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
