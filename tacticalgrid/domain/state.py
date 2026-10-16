"""Estado de la partida (datos puros, inmutable).

Representa la situación dinámica del juego: las unidades, el turno, el portador
del recurso y los contadores usados para las reglas de empate. Es inmutable:
cada cambio produce un estado nuevo. La posición de origen del recurso vive en
`Scenario`; aquí solo importa si alguien lo transporta (`portador`).
"""

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from tacticalgrid.domain.position import Position
from tacticalgrid.domain.unit import Unit


@dataclass(frozen=True)
class GameState:
    """Situación actual de la partida, completa e inmutable.

    Attributes:
        unidades: Tupla con todas las unidades (cantidad dinámica).
        turno: Bando al que le corresponde jugar ('A' o 'B').
        portador: Identificador de la unidad que transporta el recurso, o None.
        numero_turno: Cantidad de turnos ejecutados (empieza en 1).
        pases_consecutivos: Pases consecutivos registrados (empieza en 0).
        contadores: Conteo derivado de unidades por bando (calculado).
    """

    unidades: tuple[Unit, ...]
    turno: str
    portador: str | None
    numero_turno: int = 1
    pases_consecutivos: int = 0
    contadores: Mapping[str, int] = field(init=False, default_factory=dict)

    def __post_init__(self):
        """
        Purpose:
            Validar la coherencia del estado y calcular los contadores por bando.

        Preconditions:
            Las unidades, el turno y las posiciones provienen de un escenario
            ya validado y de la configuración estática (`Scenario`).

        Postconditions:
            Si es válido, guarda `unidades` como tupla y `contadores` como mapeo
            inmutable; si no, lanza ValueError.

        Complexity:
            O(U), donde U es el número de unidades.

        """
        if not isinstance(self.unidades, (tuple, list)):
            raise ValueError("Las unidades deben ser una secuencia.")

        unidades = tuple(self.unidades)
        for unidad in unidades:
            if not isinstance(unidad, Unit):
                raise ValueError("Todas las unidades deben ser de tipo Unit.")

        if self.turno not in ("A", "B"):
            raise ValueError("El turno debe ser 'A' o 'B'.")

        # Regla: una unidad por celda (sin posiciones duplicadas).
        ocupadas = set()
        for unidad in unidades:
            clave = (unidad.posicion.row, unidad.posicion.column)
            if clave in ocupadas:
                raise ValueError(
                    "Dos unidades no pueden ocupar la misma celda: "
                    f"({unidad.posicion.row}, {unidad.posicion.column})."
                )
            ocupadas.add(clave)

        # Regla: el portador debe corresponder a una unidad existente.
        if self.portador is not None:
            if not isinstance(self.portador, str) or not self.portador:
                raise ValueError("El portador debe ser un identificador válido.")
            if all(unidad.id != self.portador for unidad in unidades):
                raise ValueError(
                    f"El portador '{self.portador}' no corresponde a ninguna unidad."
                )

        if type(self.numero_turno) is not int or self.numero_turno < 1:
            raise ValueError("El número de turno debe ser un entero positivo.")

        if type(self.pases_consecutivos) is not int or self.pases_consecutivos < 0:
            raise ValueError("Los pases consecutivos no pueden ser negativos.")

        contadores = {"A": 0, "B": 0}
        for unidad in unidades:
            contadores[unidad.bando] += 1

        object.__setattr__(self, "unidades", unidades)
        object.__setattr__(self, "contadores", MappingProxyType(contadores))

    def unidades_de(self, bando: str) -> tuple[Unit, ...]:
        """
        Purpose:
            Devolver las unidades que pertenecen a un bando.

        Preconditions:
            `bando` es 'A' o 'B'.

        Postconditions:
            Devuelve una tupla (posiblemente vacía) de unidades del bando.

        Complexity:
            O(U).

        """
        return tuple(unidad for unidad in self.unidades if unidad.bando == bando)

    def unidad(self, id_unidad: str) -> Unit | None:
        """
        Purpose:
            Buscar una unidad por su identificador.

        Preconditions:
            `id_unidad` es el identificador a buscar.

        Postconditions:
            Devuelve la Unit correspondiente o None si no existe.

        Complexity:
            O(U).

        """
        for unidad in self.unidades:
            if unidad.id == id_unidad:
                return unidad
        return None

    def posicion_portador(self) -> Position | None:
        """
        Purpose:
            Obtener la posición actual de la unidad que transporta el recurso.

        Preconditions:
            El estado es válido (si hay portador, existe la unidad).

        Postconditions:
            Devuelve la Position del portador o None si nadie lo transporta.

        Complexity:
            O(U).

        """
        if self.portador is None:
            return None
        portador = self.unidad(self.portador)
        return portador.posicion if portador is not None else None

    def posicion_recurso_efectiva(self, recurso: Position) -> Position:
        """
        Purpose:
            Indicar dónde está el recurso: en el portador o en su celda de origen.

        Preconditions:
            `recurso` es la Position de origen del recurso (tomada de `Scenario`).

        Postconditions:
            Devuelve la posición del portador si existe; si no, la celda `recurso`.

        Complexity:
            O(U).

        """
        if self.portador is not None:
            posicion = self.posicion_portador()
            if posicion is not None:
                return posicion
        return recurso

    def portador_en_base(self, bases: Mapping[str, Position]) -> bool:
        """
        Purpose:
            Comprobar si el portador del recurso está en su propia base.

        Preconditions:
            `bases` mapea cada bando ('A','B') a la Position de su base.

        Postconditions:
            Devuelve True si hay portador y su posición coincide con la base de
            su bando; False en caso contrario.

        Complexity:
            O(U).

        """
        if self.portador is None:
            return False

        portador = self.unidad(self.portador)
        if portador is None:
            return False

        base = bases.get(portador.bando)
        if base is None:
            return False

        return portador.posicion.row == base.row and portador.posicion.column == base.column

    def con_portador(self, portador: str | None) -> "GameState":
        """
        Purpose:
            Crear un estado nuevo con otro portador sin mover ninguna unidad.

        Preconditions:
            `portador` es None o el identificador de una unidad existente.

        Postconditions:
            Devuelve un GameState con la misma tupla de unidades, posiciones y
            contadores, cambiando solo el portador (regla de intercepción).

        Complexity:
            O(U) por la validación del nuevo estado.

        """
        return GameState(
            unidades=self.unidades,
            turno=self.turno,
            portador=portador,
            numero_turno=self.numero_turno,
            pases_consecutivos=self.pases_consecutivos,
        )
