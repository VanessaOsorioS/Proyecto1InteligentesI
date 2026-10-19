"""Métricas de los algoritmos de decisión adversarial (Minimax y alfa-beta).

`ContadorMetricas` es mutable y lo usa el algoritmo mientras recorre el árbol.
`MetricasDecision` y `ResultadoDecision` son inmutables y son lo que se devuelve.
"""

from dataclasses import dataclass
from time import perf_counter

from tacticalgrid.domain.actions import Accion


@dataclass(frozen=True)
class MetricasDecision:
    """Medidas de una decisión tomada por Minimax o alfa-beta.

    Attributes:
        generados: Nodos hijos generados.
        expandidos: Nodos a los que se les calcularon acciones legales.
        evaluados: Hojas evaluadas con la función de utilidad.
        cortes: Podas efectivas realizadas (solo alfa-beta).
        hijos_podados: Hermanos no explorados gracias a las podas.
        profundidad_alcanzada: Nivel máximo visitado en el árbol.
        tiempo_segundos: Tiempo de pared de la decisión.
    """

    generados: int
    expandidos: int
    evaluados: int
    cortes: int
    hijos_podados: int
    profundidad_alcanzada: int
    tiempo_segundos: float


class ContadorMetricas:
    """Acumulador mutable de métricas durante una decisión."""

    def __init__(self) -> None:
        self.generados = 0
        self.expandidos = 0
        self.evaluados = 0
        self.cortes = 0
        self.hijos_podados = 0
        self._profundidad = 0
        self._inicio = perf_counter()

    def registrar_profundidad(self, nivel: int) -> None:
        """
        Purpose:
            Guardar el nivel máximo alcanzado en el árbol.

        Preconditions:
            `nivel` es un entero no negativo (0 es la raíz).

        Postconditions:
            `profundidad_alcanzada` es el máximo de los niveles registrados.

        Complexity:
            O(1).

        AI usage: Yes
        AI intervention:
            Contador auxiliar propuesto con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        self._profundidad = max(self._profundidad, nivel)

    def finalizar(self) -> MetricasDecision:
        """
        Purpose:
            Congelar los contadores en un MetricasDecision inmutable.

        Preconditions:
            Se llama una vez al terminar la decisión.

        Postconditions:
            Devuelve MetricasDecision con el tiempo transcurrido desde la creación.

        Complexity:
            O(1).

        AI usage: Yes
        AI intervention:
            Contador auxiliar propuesto con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        return MetricasDecision(
            generados=self.generados,
            expandidos=self.expandidos,
            evaluados=self.evaluados,
            cortes=self.cortes,
            hijos_podados=self.hijos_podados,
            profundidad_alcanzada=self._profundidad,
            tiempo_segundos=perf_counter() - self._inicio,
        )


@dataclass(frozen=True)
class ResultadoDecision:
    """Acción elegida por un algoritmo de decisión.

    Attributes:
        accion: Acción elegida, o None si la partida ya terminó.
        valor: Valor Minimax de la raíz desde la perspectiva del bando MAX.
        metricas: Medidas de la decisión.
    """

    accion: Accion | None
    valor: float
    metricas: MetricasDecision
