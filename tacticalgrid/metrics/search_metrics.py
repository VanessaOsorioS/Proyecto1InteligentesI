"""Métricas de rendimiento de los algoritmos de búsqueda (datos puros, inmutables).

Solo registran lo que mide el proceso de búsqueda. El resultado (camino, costo y
éxito) vive en `ResultadoBusqueda`, para no tener dos fuentes de verdad.
"""

from dataclasses import dataclass

from tacticalgrid.domain.position import Position


@dataclass(frozen=True)
class MetricasBusqueda:
    """Medidas recogidas durante una búsqueda.

    Attributes:
        generados: Nodos insertados en la frontera.
        expandidos: Nodos sacados de la frontera y expandidos.
        frontera_maxima: Mayor tamaño alcanzado por la frontera.
        tiempo_segundos: Tiempo de pared de la búsqueda.
        tiempo_heuristica_segundos: Tiempo de construcción de la heurística usada
            (0.0 en algoritmos no informados).
        orden_expansion: Nodos en el orden en que fueron expandidos.
    """

    generados: int
    expandidos: int
    frontera_maxima: int
    tiempo_segundos: float
    tiempo_heuristica_segundos: float = 0.0
    orden_expansion: tuple[Position, ...] = ()

    def __post_init__(self) -> None:
        contadores = (
            self.generados,
            self.expandidos,
            self.frontera_maxima,
        )

        if any(type(valor) is not int or valor < 0 for valor in contadores):
            raise ValueError(
                "Los contadores deben ser enteros no negativos."
            )

        if self.tiempo_segundos < 0:
            raise ValueError(
                "El tiempo no puede ser negativo."
            )

        if self.tiempo_heuristica_segundos < 0:
            raise ValueError(
                "El tiempo de la heurística no puede ser negativo."
            )

        if self.expandidos != len(self.orden_expansion):
            raise ValueError(
                "Los nodos expandidos deben coincidir "
                "con el orden de expansión."
            )

    @property
    def tiempo_total_segundos(self) -> float:
        """Tiempo de búsqueda más tiempo de construcción de la heurística."""
        return self.tiempo_segundos + self.tiempo_heuristica_segundos
