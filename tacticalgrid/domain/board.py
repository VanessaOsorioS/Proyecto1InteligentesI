
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from tacticalgrid.domain.position import Position
from tacticalgrid.domain.terrain import Terrain


@dataclass(frozen=True)
class Board:

    rows: int
    columns: int
    cells: tuple[tuple[str, ...], ...]
    terrain_types: Mapping[str, Terrain]

    def __post_init__(self):
        if type(self.rows) is not int or self.rows <= 0:
            raise ValueError("El número de filas debe ser positivo.")

        if type(self.columns) is not int or self.columns <= 0:
            raise ValueError("El número de columnas debe ser positivo.")

        # Copiamos la matriz para evitar modificaciones externas.
        cells = tuple(tuple(row) for row in self.cells)

        # Copiamos el catálogo y protegemos sus entradas.
        terrain_types = MappingProxyType(dict(self.terrain_types))

        if len(cells) != self.rows:
            raise ValueError("La cantidad de filas no coincide.")

        for row_index, row in enumerate(cells):
            if len(row) != self.columns:
                raise ValueError(
                    f"La fila {row_index} tiene una cantidad "
                    "incorrecta de columnas."
                )

            for terrain_name in row:
                if terrain_name not in terrain_types:
                    raise ValueError(
                        f"Terreno desconocido: '{terrain_name}'."
                    )

        object.__setattr__(self, "cells", cells)
        object.__setattr__(self, "terrain_types", terrain_types)

    def is_inside(self, position: Position) -> bool:
        """Indica si una posición está dentro del tablero."""
        return (
            0 <= position.row < self.rows
            and 0 <= position.column < self.columns
        )

    def get_terrain(self, position: Position) -> Terrain:
        """Obtiene el terreno de una celda."""
        if not self.is_inside(position):
            raise ValueError("La posición está fuera del tablero.")

        terrain_name = self.cells[position.row][position.column]
        return self.terrain_types[terrain_name]

    def is_walkable(self, position: Position) -> bool:
        """Indica si una celda puede atravesarse."""
        if not self.is_inside(position):
            return False

        return self.get_terrain(position).walkable

    def movement_cost(self, position: Position) -> float:
        """Obtiene el costo de ingresar a una celda."""
        terrain = self.get_terrain(position)

        if not terrain.walkable:
            raise ValueError(
                "No se puede calcular un movimiento hacia un obstáculo."
            )

        return terrain.cost
