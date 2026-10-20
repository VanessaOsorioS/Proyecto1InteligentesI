"""Motor de reglas y transición de la partida.

Implementa la lógica pura del juego: qué acciones son legales en un estado, cómo
se aplica una acción produciendo un estado nuevo (inmutable) y cómo se detectan
victorias y empates. No conoce entrada/salida ni interfaz gráfica.

Reglas cubiertas:
    - Movimiento ortogonal de una celda.
    - Una unidad por celda (bloqueo por ocupación).
    - Turnos alternados.
    - Recolección automática del recurso.
    - Transferencia entre aliados adyacentes.
    - Intercepción por un enemigo adyacente, con enfriamiento tras cada robo.
    - Pase de turno.
    - Victoria (portador en su base) y empates (límite de turnos / pases).
"""

from dataclasses import dataclass

from tacticalgrid.domain.actions import (
    Accion,
    AccionInvalida,
    Interceptar,
    Mover,
    Pasar,
    Transferir,
)
from tacticalgrid.domain.position import Position
from tacticalgrid.domain.scenario import Scenario
from tacticalgrid.domain.state import GameState
from tacticalgrid.domain.unit import Unit

LIMITE_PASES_CONSECUTIVOS = 4

TURNOS_ENTRE_ROBOS = 3
"""Turnos completos que deben pasar antes de permitir otra intercepción."""

DIRECCIONES_ORTOGONALES = ((-1, 0), (1, 0), (0, -1), (0, 1))


@dataclass(frozen=True)
class Resultado:
    """Resultado de la partida tras revisar el estado.

    Attributes:
        terminada: Indica si la partida ya finalizó.
        ganador: Bando ganador ('A'/'B') o None si hay empate.
        motivo: Descripción del desenlace ('victoria', 'empate_*') o None.
    """

    terminada: bool
    ganador: str | None = None
    motivo: str | None = None


def vecinos_ortogonales(posicion: Position) -> tuple[Position, ...]:
    """
    Purpose:
        Obtener las celdas contiguas en las cuatro direcciones ortogonales.

    Preconditions:
        `posicion` es una Position válida.

    Postconditions:
        Devuelve una tupla con las celdas vecinas de fila/columna no negativas.

    Complexity:
        O(1).

    """
    vecinos = []
    for delta_fila, delta_columna in DIRECCIONES_ORTOGONALES:
        fila = posicion.row + delta_fila
        columna = posicion.column + delta_columna
        if fila >= 0 and columna >= 0:
            vecinos.append(Position(fila, columna))
    return tuple(vecinos)


def es_adyacente(origen: Position, destino: Position) -> bool:
    """
    Purpose:
        Indicar si dos celdas son ortogonalmente adyacentes.

    Preconditions:
        `origen` y `destino` son Position válidas.

    Postconditions:
        Devuelve True si la distancia Manhattan entre ambas es exactamente 1.

    Complexity:
        O(1).

    """
    return (
        abs(origen.row - destino.row) + abs(origen.column - destino.column) == 1
    )


def celdas_ocupadas(estado: GameState) -> frozenset[tuple[int, int]]:
    """
    Purpose:
        Obtener las celdas actualmente ocupadas por unidades.

    Preconditions:
        `estado` es un GameState válido.

    Postconditions:
        Devuelve un conjunto inmutable de pares (fila, columna) ocupados.

    Complexity:
        O(U), donde U es el número de unidades.

    """
    return frozenset(
        (unidad.posicion.row, unidad.posicion.column)
        for unidad in estado.unidades
    )


def acciones_legales(estado: GameState, scenario: Scenario) -> tuple[Accion, ...]:
    """
    Purpose:
        Calcular todas las acciones válidas del bando al que le toca jugar.

    Preconditions:
        `estado` es un GameState válido y `scenario` describe el tablero y las bases.

    Postconditions:
        Devuelve una tupla de acciones legales (Mover, Transferir, Interceptar).
        `Interceptar` no aparece mientras `turnos_robo_bloqueado` sea mayor que
        cero. `Pasar` solo aparece cuando el bando no tiene ninguna otra acción
        legal disponible. Si la partida ya terminó, devuelve una tupla vacía.

    Complexity:
        O(U^2), donde U es el número de unidades.

    """
    if resultado_partida(estado, scenario) is not None:
        return ()

    tablero = scenario.tablero
    ocupadas = celdas_ocupadas(estado)
    portador = estado.unidad(estado.portador) if estado.portador is not None else None

    acciones = []

    for unidad in estado.unidades_de(estado.turno):
        # Movimiento ortogonal de una celda (bloqueo por ocupación).
        for vecino in vecinos_ortogonales(unidad.posicion):
            if not tablero.is_inside(vecino):
                continue
            if not tablero.is_walkable(vecino):
                continue
            if (vecino.row, vecino.column) in ocupadas:
                continue
            acciones.append(Mover(unidad.id, vecino))

        # Transferencia entre aliados adyacentes.
        if estado.portador is not None and unidad.id == estado.portador:
            for aliado in estado.unidades_de(estado.turno):
                if aliado.id != unidad.id and es_adyacente(
                    unidad.posicion, aliado.posicion
                ):
                    acciones.append(Transferir(unidad.id, aliado.id))

        # Intercepción de un portador enemigo adyacente, solo si el recurso
        # ya cumplió los turnos de bloqueo posteriores al último robo.
        if (
            estado.turnos_robo_bloqueado == 0
            and portador is not None
            and portador.bando != estado.turno
        ):
            if es_adyacente(unidad.posicion, portador.posicion):
                acciones.append(Interceptar(unidad.id))

    # El pase solo es legal cuando el bando no tiene otra acción disponible.
    if not acciones:
        acciones.append(Pasar())
    return tuple(acciones)


def _unidad_movida(unidad: Unit, destino: Position) -> Unit:
    """Devuelve una copia inmutable de la unidad en la nueva posición."""
    return Unit(unidad.id, unidad.bando, unidad.tipo, destino)


def _avanzar_turno(
    estado: GameState,
    unidades: tuple[Unit, ...],
    portador: str | None,
    pases_consecutivos: int,
    turnos_robo_bloqueado: int,
) -> GameState:
    """Construye el estado siguiente alternando el turno y sumando el turno."""
    return GameState(
        unidades=unidades,
        turno="B" if estado.turno == "A" else "A",
        portador=portador,
        numero_turno=estado.numero_turno + 1,
        pases_consecutivos=pases_consecutivos,
        turnos_robo_bloqueado=turnos_robo_bloqueado,
    )


def aplicar_accion(
    estado: GameState, accion: Accion, scenario: Scenario
) -> GameState:
    """
    Purpose:
        Aplicar una acción legal y devolver el estado resultante (transición pura).

    Preconditions:
        `accion` pertenece a `acciones_legales(estado, scenario)`.

    Postconditions:
        Devuelve un GameState nuevo (el original no se modifica). Actualiza la
        recogida automática, alterna el turno, ajusta los contadores y
        descuenta el bloqueo de robo (o lo reinicia si la acción es
        Interceptar). Si la acción no es legal, lanza AccionInvalida.

    Complexity:
        O(U^2), donde U es el número de unidades.

    """
    if accion not in acciones_legales(estado, scenario):
        raise AccionInvalida(f"Acción no permitida en el estado actual: {accion!r}")

    # Cualquier acción distinta de robar descuenta un turno de bloqueo.
    bloqueo_restante = max(0, estado.turnos_robo_bloqueado - 1)

    if isinstance(accion, Mover):
        unidades = tuple(
            _unidad_movida(unidad, accion.destino)
            if unidad.id == accion.unidad_id
            else unidad
            for unidad in estado.unidades
        )

        portador = estado.portador
        # Recolección automática: si nadie transporta el recurso y la unidad
        # se mueve a la celda de origen del recurso, lo recoge.
        if portador is None and accion.destino == scenario.recurso:
            portador = accion.unidad_id

        return _avanzar_turno(
            estado, unidades, portador, 0, bloqueo_restante
        )

    if isinstance(accion, Transferir):
        # Transferencia entre aliados: cambia el portador sin mover unidades.
        return _avanzar_turno(
            estado, estado.unidades, accion.destino_id, 0, bloqueo_restante
        )

    if isinstance(accion, Interceptar):
        # Intercepción: el enemigo adyacente pasa a ser el portador y se
        # reinicia el enfriamiento para evitar robos consecutivos.
        return _avanzar_turno(
            estado,
            estado.unidades,
            accion.unidad_id,
            0,
            TURNOS_ENTRE_ROBOS,
        )

    if isinstance(accion, Pasar):
        return _avanzar_turno(
            estado,
            estado.unidades,
            estado.portador,
            estado.pases_consecutivos + 1,
            bloqueo_restante,
        )

    raise AccionInvalida(f"Tipo de acción desconocido: {accion!r}")


def resultado_partida(estado: GameState, scenario: Scenario) -> Resultado | None:
    """
    Purpose:
        Determinar si la partida terminó y por qué.

    Preconditions:
        `estado` es un GameState válido y `scenario` describe las bases.

    Postconditions:
        Devuelve un Resultado si hay victoria o empate; None si sigue en curso.

    Complexity:
        O(U), donde U es el número de unidades.

    """
    if estado.portador_en_base(scenario.bases):
        portador = estado.unidad(estado.portador)
        return Resultado(True, portador.bando, "victoria")

    if estado.numero_turno > scenario.max_turnos:
        return Resultado(True, None, "empate_limite_turnos")

    if estado.pases_consecutivos >= LIMITE_PASES_CONSECUTIVOS:
        return Resultado(True, None, "empate_pases_consecutivos")

    return None


# Alias en inglés exigidos por el enunciado de la tarea.
apply_action = aplicar_accion
get_legal_actions = acciones_legales
