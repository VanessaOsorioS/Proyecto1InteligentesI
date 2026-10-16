"""Acciones del juego (datos puros, inmutables).

Cada acción describe una intención del bando en turno. No conoce el estado ni
las reglas: solo transporta los datos necesarios para que `rules` la valide y
la aplique. Son dataclasses frozen, por lo que pueden compararse y reutilizarse
sin riesgo de mutación.
"""

from dataclasses import dataclass

from tacticalgrid.domain.position import Position


class AccionInvalida(ValueError):
    """Error cuando una acción no es legal en el estado actual."""


@dataclass(frozen=True)
class Accion:
    """Clase base de toda acción del juego."""


@dataclass(frozen=True)
class Mover(Accion):
    """Desplazar una unidad a una celda contigua (ortogonal).

    Attributes:
        unidad_id: Identificador de la unidad que se mueve.
        destino: Celda de destino, adyacente a la posición actual.
    """

    unidad_id: str
    destino: Position


@dataclass(frozen=True)
class Transferir(Accion):
    """Entregar el recurso a un aliado adyacente.

    Attributes:
        origen_id: Unidad que transporta el recurso actualmente.
        destino_id: Unidad aliada que recibirá el recurso.
    """

    origen_id: str
    destino_id: str


@dataclass(frozen=True)
class Interceptar(Accion):
    """Arrebatar el recurso a un portador enemigo adyacente.

    Attributes:
        unidad_id: Unidad (del bando en turno) que intercepta el recurso.
    """

    unidad_id: str


@dataclass(frozen=True)
class Pasar(Accion):
    """Ceder el turno sin ejecutar otra acción."""
