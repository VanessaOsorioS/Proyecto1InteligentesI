import math
from functools import lru_cache

from tacticalgrid.domain.board import Board
from tacticalgrid.domain.position import Position
from tacticalgrid.domain.rules import (
    celdas_bloqueadas_para,
    es_adyacente,
    resultado_partida,
)
from tacticalgrid.domain.scenario import Scenario
from tacticalgrid.domain.state import GameState
from tacticalgrid.domain.terrain import Terrain
from tacticalgrid.domain.unit import Unit
from tacticalgrid.search.heuristics import distancias_exactas

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


def _firma_tablero(tablero: Board) -> tuple:
    """
    Purpose:
        Construir una huella inmutable y hashable del tablero para cachear mapas.

    Preconditions:
        `tablero` es un Board válido.

    Postconditions:
        Devuelve una tupla con filas, columnas, celdas y tipos de terreno.

    Complexity:
        O(T log T), T cantidad de tipos de terreno.

    AI usage: Yes
    AI intervention:
        Huella de tablero propuesta con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    terrenos = tuple(
        sorted(
            (nombre, terreno.walkable, terreno.cost)
            for nombre, terreno in tablero.terrain_types.items()
        )
    )
    return (tablero.rows, tablero.columns, tablero.cells, terrenos)


@lru_cache(maxsize=1024)
def _mapa_distancias(
    firma: tuple,
    objetivo: Position,
    bloqueadas: frozenset[Position],
) -> dict[Position, float]:
    """
    Purpose:
        Cachear el mapa de costo real mínimo hacia `objetivo` bajo un conjunto
        de celdas bloqueadas.

    Preconditions:
        `firma` proviene de `_firma_tablero`; `objetivo` es una Position;
        `bloqueadas` es un frozenset de Position.

    Postconditions:
        Devuelve un diccionario Position -> costo real mínimo. Si el objetivo
        está fuera, es un obstáculo o está bloqueado, devuelve un dict vacío.
        El diccionario se comparte entre llamadas: los consumidores no deben
        modificarlo.

    Complexity:
        O(F*C*log(F*C)) en el primer cálculo; O(1) en aciertos de caché.

    AI usage: Yes
    AI intervention:
        Caché de mapas de distancia propuesto con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    filas, columnas, celdas, terrenos = firma
    tablero = Board(
        filas,
        columnas,
        celdas,
        {nombre: Terrain(nombre, walkable, costo) for nombre, walkable, costo in terrenos},
    )

    if (
        not tablero.is_inside(objetivo)
        or not tablero.is_walkable(objetivo)
        or objetivo in bloqueadas
    ):
        return {}

    return distancias_exactas(tablero, (objetivo,), bloqueadas)


def _maximo_finito(mapa: dict[Position, float]) -> float:
    """
    Purpose:
        Obtener el mayor costo finito de un mapa de distancias.

    Preconditions:
        `mapa` asocia posiciones con costos reales o infinitos.

    Postconditions:
        Devuelve el máximo finito, o 0.0 si no hay ninguno.

    Complexity:
        O(N), N cantidad de posiciones del mapa.

    AI usage: Yes
    AI intervention:
        Normalización auxiliar propuesta con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    finitos = [costo for costo in mapa.values() if math.isfinite(costo)]
    return max(finitos) if finitos else 0.0


def _normalizar(costo: float, maximo: float) -> float:
    """
    Purpose:
        Escalar un costo real al intervalo [0, 1] usando `maximo` como referencia.

    Preconditions:
        `costo` es un costo real o infinito; `maximo` es >= 0.

    Postconditions:
        Devuelve 0.0 si el costo es 0; 1.0 si no hay ruta o si el costo alcanza
        o supera el máximo. Un máximo 0 con costo 0 se interpreta como 0.0.

    Complexity:
        O(1).

    AI usage: Yes
    AI intervention:
        Normalización de la distancia exacta propuesta con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    if not math.isfinite(costo):
        return 1.0
    if maximo <= 0:
        return 0.0 if costo == 0 else 1.0
    return min(1.0, costo / maximo)


def _distancia_normalizada(
    estado: GameState,
    unidad: Unit,
    objetivo: Position,
    scenario: Scenario,
) -> float:
    """
    Purpose:
        Medir la distancia real normalizada de una unidad a un objetivo,
        respetando muros, costos y ocupación.

    Preconditions:
        `estado` es válido; `unidad` pertenece al estado; `objetivo` es la meta;
        `scenario` es el escenario de la partida.

    Postconditions:
        Devuelve un valor en [0, 1]. 0.0 significa que la unidad está sobre el
        objetivo; 1.0 significa que no hay ruta o que su costo es el mayor
        posible del tablero para esa meta.

    Complexity:
        O(F*C*log(F*C)) en el primer cálculo y O(1) con caché.

    AI usage: Yes
    AI intervention:
        Distancia exacta con ocupación propuesta con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    firma = _firma_tablero(scenario.tablero)
    maximo = _maximo_finito(_mapa_distancias(firma, objetivo, frozenset()))
    bloqueadas = celdas_bloqueadas_para(estado, scenario, unidad)
    costo = _mapa_distancias(firma, objetivo, bloqueadas).get(unidad.posicion, math.inf)
    return _normalizar(costo, maximo)


def _minima_distancia_a(
    estado: GameState,
    bando: str,
    objetivo: Position,
    scenario: Scenario,
) -> float:
    """
    Purpose:
        Obtener la menor distancia real normalizada de un bando a un objetivo.

    Preconditions:
        `estado` es válido; `bando` es 'A' o 'B'; `objetivo` es una Position;
        `scenario` es válido.

    Postconditions:
        Devuelve un valor en [0, 1]; si el bando no tiene unidades, 1.0.

    Complexity:
        O(U * F*C*log(F*C)) sin caché; O(U) con mapas cacheados.

    AI usage: Yes
    AI intervention:
        Distancia mínima propuesta con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    distancias = [
        _distancia_normalizada(estado, unidad, objetivo, scenario)
        for unidad in estado.unidades_de(bando)
    ]
    if not distancias:
        # Un bando sin unidades nunca estará "cerca": peor caso normalizado.
        return 1.0
    return min(distancias)


def _unidades_adyacentes_a(
    estado: GameState, bando: str, objetivo: Position
) -> int:
    """
    Purpose:
        Contar las unidades de un bando ortogonalmente adyacentes a una celda.

    Preconditions:
        `estado` es válido; `bando` es 'A' o 'B'; `objetivo` es una Position.

    Postconditions:
        Devuelve el número de unidades adyacentes; no modifica el estado.

    Complexity:
        O(U), U cantidad de unidades del bando.

    AI usage: Yes
    AI intervention:
        Conteo de adyacencias propuesto con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    return sum(
        1
        for unidad in estado.unidades_de(bando)
        if es_adyacente(unidad.posicion, objetivo)
    )


def _progreso_portador(
    estado: GameState,
    portador: Unit,
    base: Position | None,
    scenario: Scenario,
) -> float:
    """
    Purpose:
        Medir el progreso de un portador hacia su base en [0, 1] con distancia real.

    Preconditions:
        `estado` es válido; `portador` pertenece al estado; `base` es la Position
        de la base de SU bando (o None); `scenario` es un Scenario válido.

    Postconditions:
        Devuelve 1 - distancia_real_normalizada, es decir 1.0 sobre la base y
        0.0 si no hay ruta. Modela muros, costos de terreno y ocupación.

    Complexity:
        O(F*C*log(F*C)) en el primer cálculo; O(1) con caché.

    AI usage: Yes
    AI intervention:
        Progreso con distancia exacta propuesto con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    if base is None:
        return 0.0
    return 1.0 - _distancia_normalizada(estado, portador, base, scenario)


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
        El progreso y el control usan la distancia real con Dijkstra: modelan
        muros, costos de terreno y ocupación de unidades.
        No modifica `estado` ni `scenario`.

    Complexity:
        O(U * F*C*log(F*C)) en el peor caso sin caché; O(U) con mapas cacheados.

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

        # 2) Portador: posesión fija + progreso real hacia la base de SU bando.
        #    Se suma si el portador es de MAX; se resta si es de MIN.
        base_portador = scenario.bases.get(portador.bando)
        progreso = _progreso_portador(estado, portador, base_portador, scenario)
        valor_portador = PESO_POSESION + PESO_PROGRESO * progreso
        valor += valor_portador if es_aliado else -valor_portador

        # 3) Riesgo de intercepción: unidades enemigas adyacentes al portador
        # aliado (riesgo, penaliza) o unidades aliadas adyacentes al portador
        # enemigo (oportunidad de interceptar, premia). Mientras el recurso
        # está bloqueado ninguna intercepción es legal, así que el término no
        # aplica.
        if estado.turnos_robo_bloqueado == 0:
            adyacentes = _unidades_adyacentes_a(
                estado, bando_min if es_aliado else bando_max, portador.posicion
            )
            valor += (
                -PESO_RIESGO * adyacentes if es_aliado else PESO_RIESGO * adyacentes
            )
    else:
        # 4) Control de la celda del recurso mientras nadie lo transporta.
        cerca_max = _minima_distancia_a(estado, bando_max, scenario.recurso, scenario)
        cerca_min = _minima_distancia_a(estado, bando_min, scenario.recurso, scenario)
        valor += PESO_RECURSO * (cerca_min - cerca_max)

    # Clamp defensivo: garantiza |heurística| <= LIMITE_HEURISTICA < VICTORIA.
    return max(-LIMITE_HEURISTICA, min(LIMITE_HEURISTICA, valor))
