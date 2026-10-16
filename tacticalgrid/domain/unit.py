"""Entidad de unidad del juego (datos puros, inmutable)."""

from dataclasses import dataclass

from tacticalgrid.domain.position import Position


@dataclass(frozen=True)
class Unit:
    """Unidad de un bando situada en una celda del tablero.

    Attributes:
        id: Identificador único de la unidad dentro del escenario.
        bando: Equipo al que pertenece, 'A' o 'B'.
        tipo: Tipo o clase de la unidad (p. ej. 'estandar').
        posicion: Coordenada (fila, columna) que ocupa la unidad.
    """

    id: str
    bando: str
    tipo: str
    posicion: Position

    def __post_init__(self):
        """
        Purpose:
            Validar que la unidad tenga identificador, bando, tipo y posición
            coherentes con las reglas del dominio.

        Preconditions:
            Los campos provienen de un escenario ya validado.

        Postconditions:
            Si es válida, construye la unidad; si no, lanza ValueError.

        Complexity:
            O(1).

        AI usage: Yes
        AI intervention:
            Validaciones propuestas con asistencia de IA a partir del modelo
            de Position y Terrain existente.

        """
        if not isinstance(self.id, str) or not self.id:
            raise ValueError("La unidad necesita un identificador válido.")

        if self.bando not in ("A", "B"):
            raise ValueError("El bando de la unidad debe ser 'A' o 'B'.")

        if not isinstance(self.tipo, str) or not self.tipo:
            raise ValueError("La unidad necesita un tipo válido.")

        if not isinstance(self.posicion, Position):
            raise ValueError("La posición debe ser una instancia de Position.")
