from tacticalgrid.domain.position import Position
from tacticalgrid.domain.rules import es_adyacente, resultado_partida
from tacticalgrid.domain.scenario import Scenario
from tacticalgrid.domain.state import GameState

#Escala de utilidad

VICTORIA = 1000.0
"""Valor asignado a una victoria de MAX. Cota superior estricta."""

DERROTA = -1000.0
"""Valor asignado a una derrota de MAX. Cota inferior estricta."""

EMPATE = 0.0
"""Valor asignado a estados terminales sin ganador."""

LIMITE_HEURISTICA = 100.0
"""Cota absoluta de la heurística; garantiza que el terminal siempre domina."""

#Pesos de la heurística

PESO_POSESION = 20.0
"""Bonificación fija por poseer (o no) el recurso, exista o no progreso."""

PESO_PROGRESO = 30.0
"""Peso máximo del componente de progreso del portador hacia su base."""

PESO_RECURSO = 15.0
"""Peso máximo del término de control de la celda del recurso."""

PESO_RIESGO = 5.0
"""Peso por cada unidad adyacente al portador (riesgo u oportunidad)."""


def distancia_manhattan(origen: Position, destino: Position) -> int:
    """
    Purpose:
        Medir la distancia en celdas entre dos posiciones (movimientos ortogonales).

    Preconditions:
        `origen` y `destino` son Position válidas.

    Postconditions:
        Devuelve la suma de diferencias absolutas de fila y columna. Coincide
        con el número mínimo de acciones `Mover` necesarias sin obstáculos.

    Complexity:
        O(1).

    AI usage: Yes
    AI intervention:
        Función auxiliar propuesta con asistencia de IA.
        
    Student validation:
        Pendiente de revisión por el equipo.
    """
    return abs(origen.row - destino.row) + abs(origen.column - destino.column)


def _normalizar(distancia: int, scenario: Scenario) -> float:
    """Escala una distancia al intervalo [0, 1] según el tamaño del tablero."""
    maximo = (scenario.tablero.rows - 1) + (scenario.tablero.columns - 1)
    if maximo <= 0:
        return 0.0
    return min(1.0, distancia / maximo)


def _minima_distancia_a(
    positions: tuple[Position, ...], objetivo: Position, scenario: Scenario
) -> float:
    """Menor distancia (normalizada) de un conjunto de posiciones a un objetivo."""
    if not positions:
        # Un bando sin unidades nunca estará "cerca": peor caso normalizado.
        return 1.0
    return _normalizar(
        min(distancia_manhattan(pos, objetivo) for pos in positions), scenario
    )


def _unidades_adyacentes_a(
    estado: GameState, bando: str, objetivo: Position
) -> int:
    """Cuenta las unidades de `bando` ortogonalmente adyacentes a `objetivo`."""
    return sum(
        1
        for unidad in estado.unidades_de(bando)
        if es_adyacente(unidad.posicion, objetivo)
    )


def _progreso_portador(
    posicion: Position, base: Position | None, scenario: Scenario
) -> float:
    """
    Purpose:
        Medir el progreso de un portador hacia su base en [0, 1].

    Preconditions:
        `posicion` es la Position del portador; `base` es la Position de la
        base de SU bando (o None); `scenario` es un Scenario válido.

    Postconditions:
        Devuelve 1 - distancia_normalizada, es decir 1.0 en la base y 0.0 a la
        distancia máxima del tablero. Si `base` es None, devuelve 0.0.
        Es una aproximación geométrica (Manhattan): no considera muros ni
        ocupación de casillas.

    Complexity:
        O(1).

    AI usage: Yes
    AI intervention:
        Función auxiliar propuesta con asistencia de IA (revisión del equipo).
    Student validation:
        Pendiente de revisión por el equipo.
    """
    if base is None:
        return 0.0
    return 1.0 - _normalizar(distancia_manhattan(posicion, base), scenario)


def utilidad_terminal(
    estado: GameState, scenario: Scenario, bando_max: str
) -> float | None:
    """
    Purpose:
        Obtener la utilidad exacta de un estado terminal respecto de `bando_max`.

    Preconditions:
        `estado` y `scenario` son válidos; `bando_max` es 'A' o 'B'.

    Postconditions:
        Devuelve VICTORIA si el ganador es `bando_max`; DERROTA si el ganador
        es el bando contrario; EMPATE si el empate por límite de turnos o
        pases consecutivos. Devuelve None si el estado no es terminal.

    Complexity:
        O(U), donde U es el número de unidades.

    AI usage: Yes
    AI intervention:
        Función auxiliar propuesta con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    if bando_max not in ("A", "B"):
        raise ValueError("El bando MAX debe ser 'A' o 'B'.")

    resultado = resultado_partida(estado, scenario)
    if resultado is None:
        return None
    if resultado.ganador is None:
        return EMPATE
    return VICTORIA if resultado.ganador == bando_max else DERROTA


def evaluar_estado(estado: GameState, scenario: Scenario, bando_max: str) -> float:
    """
    Purpose:
        Evaluar un estado desde la perspectiva de `bando_max`.

    Preconditions:
        `estado` y `scenario` son válidos; `bando_max` es 'A' o 'B'.

    Postconditions:
        Devuelve un float:
        - VICTORIA (+1000) si la partida terminó con victoria de `bando_max`.
        - DERROTA (-1000) si terminó con victoria del bando contrario.
        - EMPATE (0) si terminó en empate.
        - Un valor heurístico en [-LIMITE_HEURISTICA, LIMITE_HEURISTICA] si la
          partida sigue en curso, combinando posesión + progreso del portador,
          control del recurso libre y riesgo de intercepción.
        Los estados terminales se evalúan ANTES que la heurística: un portador
        que alcanza su propia base produce +/-VICTORIA, nunca el valor
        heurístico de progreso.
        No modifica `estado` ni `scenario`.

    Complexity:
        O(U), donde U es el número de unidades.

    AI usage: Yes
    AI intervention:
        Función de evaluación propuesta con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    if bando_max not in ("A", "B"):
        raise ValueError("El bando MAX debe ser 'A' o 'B'.")

    # 1) Estados terminales: utilidad exacta, prioridad absoluta.
    terminal = utilidad_terminal(estado, scenario, bando_max)
    if terminal is not None:
        return terminal

    bando_min = "B" if bando_max == "A" else "A"
    valor = 0.0

    portador = estado.unidad(estado.portador) if estado.portador is not None else None

    if portador is not None:
        es_aliado = portador.bando == bando_max

        # 2) Portador: posesión fija + progreso hacia la base de SU bando.
        #    Se suma si el portador es de MAX; se resta si es de MIN.
        base_portador = scenario.bases.get(portador.bando)
        progreso = _progreso_portador(portador.posicion, base_portador, scenario)
        valor_portador = PESO_POSESION + PESO_PROGRESO * progreso
        valor += valor_portador if es_aliado else -valor_portador

        # 3) Riesgo de intercepción: unidades enemigas adyacentes al portador
        # aliado (riesgo, penaliza) o unidades aliadas adyacentes al portador
        # enemigo (oportunidad de interceptar, premia).
        adyacentes = _unidades_adyacentes_a(
            estado, bando_min if es_aliado else bando_max, portador.posicion
        )
        valor += -PESO_RIESGO * adyacentes if es_aliado else PESO_RIESGO * adyacentes
    else:
        # 4) Control de la celda del recurso mientras nadie lo transporta.
        posiciones_max = tuple(
            unidad.posicion for unidad in estado.unidades_de(bando_max)
        )
        posiciones_min = tuple(
            unidad.posicion for unidad in estado.unidades_de(bando_min)
        )
        cerca_max = _minima_distancia_a(posiciones_max, scenario.recurso, scenario)
        cerca_min = _minima_distancia_a(posiciones_min, scenario.recurso, scenario)
        valor += PESO_RECURSO * (cerca_min - cerca_max)

    # Clamp defensivo: garantiza |heurística| <= LIMITE_HEURISTICA < VICTORIA.
    return max(-LIMITE_HEURISTICA, min(LIMITE_HEURISTICA, valor))
