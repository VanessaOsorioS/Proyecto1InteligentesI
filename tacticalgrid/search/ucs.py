
"""Búsqueda de costo uniforme (UCS) para TacticalGrid."""

import heapq
from itertools import count
from time import perf_counter

from tacticalgrid.domain.position import Position
from tacticalgrid.metrics.search_metrics import MetricasBusqueda
from tacticalgrid.search.problem import Problema, ResultadoBusqueda


def reconstruir_camino(
    padres: dict[Position, Position | None],
    objetivo: Position,
) -> tuple[Position, ...]:
    """Reconstruir el camino desde el inicio hasta la meta."""
    camino = []
    actual = objetivo

    while actual is not None:
        camino.append(actual)
        actual = padres[actual]

    camino.reverse()
    return tuple(camino)


def ucs(problema: Problema) -> ResultadoBusqueda:
    """
    Purpose:
        Encontrar la ruta de menor costo acumulado desde el inicio
        hasta una posición objetivo mediante búsqueda de costo uniforme.

    Preconditions:
        El problema tiene un inicio válido, una cantidad finita de
        estados alcanzables y costos de transición estrictamente
        positivos, como los terrenos de TacticalGrid.

    Postconditions:
        Devuelve un ResultadoBusqueda con el camino óptimo en costo,
        el costo acumulado y las métricas correspondientes.
        Si no existe ruta, devuelve exito=False.
        No modifica el problema recibido.

    Complexity:
        En un grafo finito, utilizando heapq y permitiendo entradas
        repetidas, el tiempo depende de la cantidad de inserciones
        realizadas en la cola de prioridad; para este tablero con
        grado máximo 4 es O((V + E) log (V + E)) y el espacio
        O(V + E), bajo el supuesto de costos no negativos.
    """

    inicio_tiempo = perf_counter()

    # Evita comparar Position cuando hay costos iguales.
    desempate = count()

    # Cada entrada: (costo acumulado, orden de inserción, posición).
    frontera = [
        (0.0, next(desempate), problema.inicio)
    ]

    mejor_costo: dict[Position, float] = {
        problema.inicio: 0.0
    }

    padres: dict[Position, Position | None] = {
        problema.inicio: None
    }

    expandidos_definitivos: set[Position] = set()

    generados = 1
    frontera_maxima = 1
    orden_expansion: list[Position] = []

    while frontera:
        costo_actual, _, actual = heapq.heappop(frontera)

        # Ignorar entradas de prioridad que ya quedaron obsoletas.
        if costo_actual > mejor_costo[actual]:
            continue

        # No expandir nuevamente posiciones ya resueltas.
        if actual in expandidos_definitivos:
            continue

        # La primera vez que la meta sale de la cola con
        # su mejor costo, la ruta es óptima.
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
                costo=costo_actual,
                exito=True,
                metricas=metricas,
            )

        expandidos_definitivos.add(actual)
        orden_expansion.append(actual)

        for vecino, costo_paso in problema.sucesores(actual):
            if costo_paso <= 0:
                raise ValueError(
                    "UCS requiere costos de transición positivos."
                )

            if vecino in expandidos_definitivos:
                continue

            nuevo_costo = costo_actual + costo_paso

            # Actualizar solo si encontramos una ruta más barata.
            if nuevo_costo < mejor_costo.get(
                vecino, float("inf")
            ):
                mejor_costo[vecino] = nuevo_costo
                padres[vecino] = actual

                heapq.heappush(
                    frontera,
                    (
                        nuevo_costo,
                        next(desempate),
                        vecino,
                    ),
                )

                generados += 1

        frontera_maxima = max(
            frontera_maxima,
            len(frontera),
        )

    # La meta no es alcanzable.
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
