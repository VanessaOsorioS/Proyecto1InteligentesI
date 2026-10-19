"""Beam Search sobre un `Problema` con ancho de haz `k` configurable.


Avanza por niveles. En cada nivel expande los nodos del haz, genera sus vecinos y
conserva solo los `k` más prometedores según la heurística h(n). Las alternativas
descartadas se pierden: no hay lista de respaldo. Por eso `k` limita de verdad la
exploración, pero la ruta puede no ser la de costo mínimo.
"""


import math
import time
from typing import Callable


from tacticalgrid.domain.position import Position
from tacticalgrid.metrics.search_metrics import MetricasBusqueda
from tacticalgrid.search.problem import Problema, ResultadoBusqueda




def buscar(
    problema: Problema,
    heuristica: Callable[[Position], float],
    ancho_haz: int,
) -> ResultadoBusqueda:
    """
    Purpose:
        Buscar una ruta al objetivo manteniendo como máximo `ancho_haz` nodos por nivel.


    Preconditions:
        `problema` cumple la interfaz `Problema`; `heuristica` estima el costo restante;
        `ancho_haz` es un entero mayor o igual que 1.


    Postconditions:
        Si encuentra la meta, devuelve su camino y el costo real acumulado (puede no
        ser el mínimo). Si el haz se vacía sin llegar a la meta, devuelve exito=False.
        Ningún nivel conserva más de `ancho_haz` nodos. Cada celda se expande una vez.
        No guarda estado entre llamadas.


    Complexity:
        O(d * k * b * log(k * b)), con profundidad d alcanzada, k ancho de haz y b
        factor de ramificación (a lo sumo 4 en el tablero ortogonal).


    """
    if type(ancho_haz) is not int or ancho_haz < 1:
        raise ValueError("El ancho del haz debe ser un entero mayor o igual que 1.")


    inicio_tiempo = time.perf_counter()


    haz: list[tuple[Position, float, tuple[Position, ...]]] = [
        (problema.inicio, 0.0, (problema.inicio,))
    ]
    expandidos: set[Position] = set()
    orden: list[Position] = []
    generados = 0
    frontera_maxima = 1


    while haz:
        candidatos: dict[Position, tuple[float, float, tuple[Position, ...]]] = {}


        for nodo, g, camino in haz:
            if problema.es_objetivo(nodo):
                metricas = MetricasBusqueda(
                    generados=generados,
                    expandidos=len(orden),
                    frontera_maxima=frontera_maxima,
                    tiempo_segundos=time.perf_counter() - inicio_tiempo,
                    orden_expansion=tuple(orden),
                )
                return ResultadoBusqueda(camino, g, True, metricas)


            expandidos.add(nodo)
            orden.append(nodo)


            for vecino, costo in problema.sucesores(nodo):
                if vecino in expandidos:
                    continue


                nuevo_g = g + costo
                h = heuristica(vecino)
                if h == math.inf:
                    continue


                generados += 1
                previo = candidatos.get(vecino)
                # Deduplicación dentro del nivel: conserva el mejor g.
                if previo is not None and previo[0] <= nuevo_g:
                    continue
                candidatos[vecino] = (nuevo_g, h, camino + (vecino,))


        frontera_maxima = max(frontera_maxima, len(candidatos))


        # Poda: ordenar por h, luego por g y finalmente por posición (determinista).
        ordenados = sorted(
            candidatos.items(),
            key=lambda item: (item[1][1], item[1][0], item[0].row, item[0].column),
        )
        haz = [
            (posicion, g, camino)
            for posicion, (g, _, camino) in ordenados[:ancho_haz]
        ]


    metricas = MetricasBusqueda(
        generados=generados,
        expandidos=len(orden),
        frontera_maxima=frontera_maxima,
        tiempo_segundos=time.perf_counter() - inicio_tiempo,
        orden_expansion=tuple(orden),
    )
    return ResultadoBusqueda((), math.inf, False, metricas)
