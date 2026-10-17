"""Contrato común de navegación para los algoritmos de búsqueda.

Un problema describe un estado inicial, una condición de meta y los sucesores con
su costo de transición. `ProblemaTablero` implementa el caso de una unidad que
recorre el tablero según el terreno. No conoce pygame ni la interfaz.
"""

from dataclasses import dataclass
from typing import Iterable, Protocol

from tacticalgrid.domain.board import Board
from tacticalgrid.domain.position import Position
from tacticalgrid.domain.rules import vecinos_ortogonales
from tacticalgrid.metrics.search_metrics import MetricasBusqueda


@dataclass(frozen=True)
class ResultadoBusqueda:
    """Resultado de un algoritmo de búsqueda.

    Attributes:
        camino: Posiciones desde el inicio hasta la meta (vacío si no hay ruta).
        costo: Costo total del camino (infinito si no hay ruta).
        exito: Indica si se encontró una ruta.
        metricas: Medidas recogidas durante la búsqueda.
    """

    camino: tuple[Position, ...]
    costo: float
    exito: bool
    metricas: MetricasBusqueda

    @property
    def longitud(self) -> int:
        """Número de movimientos de la ruta (nodos del camino menos uno)."""
        return max(0, len(self.camino) - 1)


class Problema(Protocol):
    """Interfaz que deben cumplir todos los problemas de búsqueda."""

    inicio: Position

    def es_objetivo(self, posicion: Position) -> bool:
        """Indica si la posición cumple la meta."""

    def sucesores(self, posicion: Position) -> Iterable[tuple[Position, float]]:
        """Devuelve pares (vecino, costo de transición) alcanzables desde `posicion`."""


class ProblemaTablero:
    """Recorrido ortogonal de una unidad sobre el tablero según el terreno.

    Attributes:
        tablero: Tablero con terrenos transitables y costos.
        inicio: Posición de partida.
        objetivo: Posición que se quiere alcanzar.
        bloqueadas: Celdas adicionales que no se pueden atravesar (vacío por defecto).
    """

    def __init__(
        self,
        tablero: Board,
        inicio: Position,
        objetivo: Position,
        bloqueadas: frozenset[Position] = frozenset(),
    ):
        """
        Purpose:
            Crear el problema validando que inicio y meta sean celdas transitables.

        Preconditions:
            `tablero` es un Board; `inicio`, `objetivo` son Position; `bloqueadas`
            es un frozenset de Position.

        Postconditions:
            Guarda los datos; lanza ValueError si inicio u objetivo están fuera
            del tablero, sobre un obstáculo o bloqueados.

        Complexity:
            O(1).

        """
        for nombre, celda in (("inicio", inicio), ("objetivo", objetivo)):
            if not tablero.is_inside(celda):
                raise ValueError(f"El {nombre} está fuera del tablero.")

            if not tablero.is_walkable(celda):
                raise ValueError(f"El {nombre} está sobre un obstáculo.")

            if celda in bloqueadas:
                raise ValueError(f"El {nombre} está bloqueado.")

        if any(not isinstance(p, Position) for p in bloqueadas):
            raise ValueError("Todas las celdas bloqueadas deben ser Position.")

        self.tablero = tablero
        self.inicio = inicio
        self.objetivo = objetivo
        self.bloqueadas = frozenset(bloqueadas)

    def es_objetivo(self, posicion: Position) -> bool:
        """
        Purpose:
            Comprobar si una posición es la meta.

        Preconditions:
            `posicion` es una Position.

        Postconditions:
            Devuelve True solo si coincide con `objetivo`.

        Complexity:
            O(1).

        """
        return posicion == self.objetivo

    def sucesores(self, posicion: Position) -> tuple[tuple[Position, float], ...]:
        """
        Purpose:
            Listar los vecinos ortogonales transitables y el costo de entrar a cada uno.

        Preconditions:
            `posicion` es una Position válida del tablero.

        Postconditions:
            Devuelve pares (vecino, costo) en orden determinista. El costo es el de
            ingresar a la celda vecina; la celda de origen no se cobra aquí.

        Complexity:
            O(1), con a lo sumo cuatro vecinos.

        """
        resultado = []
        for vecino in vecinos_ortogonales(posicion):
            if not self.tablero.is_inside(vecino) or not self.tablero.is_walkable(vecino):
                continue
            if vecino in self.bloqueadas:
                continue
            resultado.append((vecino, self.tablero.movement_cost(vecino)))
        return tuple(resultado)


def objetivos_adyacentes(
    tablero: Board,
    objetivo: Position,
    bloqueadas: frozenset[Position] = frozenset(),
) -> tuple[Position, ...]:
    """
    Purpose:
        Listar las celdas transitables vecinas a `objetivo` que no estén bloqueadas,
        para aproximarse a una celda ocupada (p. ej. una unidad enemiga) sin
        atravesarla.

    Preconditions:
        `tablero` es un Board; `objetivo` es una Position; `bloqueadas` es un
        iterable de Position con las celdas no disponibles (ocupación).

    Postconditions:
        Devuelve una tupla de Position en orden determinista. Puede estar vacía si
        `objetivo` no tiene vecinos libres. Lanza ValueError si algún elemento de
        `bloqueadas` no es Position.

    Complexity:
        O(1), con a lo sumo cuatro vecinos.

    """
    if any(not isinstance(p, Position) for p in bloqueadas):
        raise ValueError("Todas las celdas bloqueadas deben ser Position.")

    resultado = []
    for vecino in vecinos_ortogonales(objetivo):
        if not tablero.is_inside(vecino) or not tablero.is_walkable(vecino):
            continue
        if vecino in bloqueadas:
            continue
        resultado.append(vecino)
    return tuple(resultado)