"""Configuración estática de un escenario (datos puros, inmutable).

Agrupa el tablero, las bases, la ubicación inicial del recurso y los datos de
configuración del juego. No contiene información que cambie durante la partida;
esa responsabilidad es de `GameState`.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from tacticalgrid.domain.board import Board
from tacticalgrid.domain.position import Position


@dataclass(frozen=True)
class Scenario:
    """Configuración inmutable de un escenario cargado desde JSON.

    Attributes:
        version: Versión del formato del escenario (p. ej. '1.0').
        tablero: Tablero con dimensiones, terrenos y transitabilidad.
        bases: Posición de la base de cada bando ('A' y 'B').
        recurso: Posición inicial del recurso en el tablero.
        profundidad_maxima_minimax: Profundidad opcional para Minimax.
        max_turnos: Límite de turnos ejecutados antes del empate (por defecto 200).
        prueba: Bloque opcional de configuración de pruebas (se conserva tal cual).
    """

    version: str
    tablero: Board
    bases: Mapping[str, Position]
    recurso: Position
    profundidad_maxima_minimax: int | None = None
    max_turnos: int = 200
    prueba: Mapping[str, Any] | None = None

    def __post_init__(self):
        """
        Purpose:
            Validar la coherencia de la configuración y congelar los
            contenedores mutables para garantizar inmutabilidad.

        Preconditions:
            `tablero` es un Board y las posiciones provienen de un escenario
            ya validado por `validate_scenario`.

        Postconditions:
            Si es válido, guarda contenedores inmutables; si no, lanza ValueError.

        Complexity:
            O(B), donde B es el número de posiciones de base (constante).

        """
        if not isinstance(self.version, str) or not self.version:
            raise ValueError("La versión del escenario debe ser un texto no vacío.")

        if not isinstance(self.tablero, Board):
            raise ValueError("El tablero debe ser una instancia de Board.")

        if not isinstance(self.recurso, Position):
            raise ValueError("El recurso debe ser una instancia de Position.")

        if not self.tablero.is_inside(self.recurso):
            raise ValueError("El recurso está fuera del tablero.")

        if not self.tablero.is_walkable(self.recurso):
            raise ValueError("El recurso no puede estar sobre un obstáculo.")

        if not isinstance(self.bases, Mapping):
            raise ValueError("Las bases deben ser un mapeo bando -> Position.")

        bases = {}
        for bando, posicion in self.bases.items():
            if bando not in ("A", "B"):
                raise ValueError(f"Bando de base inválido: '{bando}'.")
            if not isinstance(posicion, Position):
                raise ValueError(
                    f"La base '{bando}' debe ser una instancia de Position."
                )
            if not self.tablero.is_inside(posicion):
                raise ValueError(f"La base '{bando}' está fuera del tablero.")
            if not self.tablero.is_walkable(posicion):
                raise ValueError(f"La base '{bando}' está sobre un obstáculo.")
            bases[bando] = posicion

        if "A" not in bases or "B" not in bases:
            raise ValueError("Deben existir las bases 'A' y 'B'.")

        if self.profundidad_maxima_minimax is not None:
            if (
                type(self.profundidad_maxima_minimax) is not int
                or self.profundidad_maxima_minimax < 1
            ):
                raise ValueError(
                    "La profundidad máxima de Minimax debe ser un entero positivo."
                )

        if type(self.max_turnos) is not int or self.max_turnos < 1:
            raise ValueError("El límite de turnos debe ser un entero positivo.")

        if self.prueba is not None and not isinstance(self.prueba, Mapping):
            raise ValueError("El bloque 'prueba' debe ser un mapeo.")

        object.__setattr__(self, "bases", MappingProxyType(bases))
        if self.prueba is not None:
            object.__setattr__(
                self, "prueba", MappingProxyType(dict(self.prueba))
            )
