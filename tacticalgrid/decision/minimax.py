from tacticalgrid.decision.utility import evaluar_estado
from tacticalgrid.domain.rules import (
    acciones_legales,
    aplicar_accion,
    resultado_partida,
)
from tacticalgrid.domain.scenario import Scenario
from tacticalgrid.domain.state import GameState
from tacticalgrid.metrics.decision_metrics import (
    ContadorMetricas,
    ResultadoDecision,
)

PROFUNDIDAD_POR_DEFECTO = 3
"""Profundidad usada cuando ni el argumento ni el escenario la fijan."""


def profundidad_efectiva(scenario: Scenario, profundidad: int | None = None) -> int:
    """
    Purpose:
        Resolver la profundidad de búsqueda según la precedencia acordada.

    Preconditions:
        `scenario` es un Scenario válido; `profundidad` es None o un entero
        positivo.

    Postconditions:
        Devuelve `profundidad` si se pasó; si no, `scenario.profundidad_maxima_minimax`
        si está definida; en otro caso PROFUNDIDAD_POR_DEFECTO (3).
        Lanza ValueError si `profundidad` no es un entero positivo.

    Complexity:
        O(1).

    """
    if profundidad is not None:
        if type(profundidad) is not int or profundidad < 1:
            raise ValueError("La profundidad debe ser un entero positivo.")
        return profundidad
    if scenario.profundidad_maxima_minimax is not None:
        return scenario.profundidad_maxima_minimax
    return PROFUNDIDAD_POR_DEFECTO


def _valor_minimax(
    estado: GameState,
    scenario: Scenario,
    bando_max: str,
    restante: int,
    nivel: int,
    contador: ContadorMetricas,
) -> float:
    """Valor Minimax de `estado` con `restante` niveles por jugar (recursión)."""
    contador.registrar_profundidad(nivel)

    # Hoja: estado terminal o profundidad agotada -> función de utilidad.
    if resultado_partida(estado, scenario) is not None or restante == 0:
        contador.evaluados += 1
        return evaluar_estado(estado, scenario, bando_max)

    acciones = acciones_legales(estado, scenario)
    contador.expandidos += 1

    # El bando en turno es MAX si coincide con `bando_max`; si no, es MIN.
    es_max = estado.turno == bando_max

    mejor = None
    for accion in acciones:
        hijo = aplicar_accion(estado, accion, scenario)
        contador.generados += 1
        valor_hijo = _valor_minimax(
            hijo, scenario, bando_max, restante - 1, nivel + 1, contador
        )
        # Comparación estricta: en empates se conserva la primera acción.
        if mejor is None or (es_max and valor_hijo > mejor) or (
            (not es_max) and valor_hijo < mejor
        ):
            mejor = valor_hijo

    if mejor is None:
        # Inalcanzable: si el estado no es terminal, siempre hay al menos una
        # acción (Pasar es legal cuando no hay otra). Se deja constancia.
        contador.evaluados += 1
        return evaluar_estado(estado, scenario, bando_max)

    return mejor


def minimax(
    estado: GameState,
    scenario: Scenario,
    profundidad: int | None = None,
    bando_max: str | None = None,
) -> ResultadoDecision:
    """
    Purpose:
        Elegir la acción del bando en turno (o de `bando_max`) mediante Minimax
        con profundidad limitada.

    Preconditions:
        `estado` y `scenario` son válidos y coherentes; `profundidad` es None o
        un entero positivo; `bando_max` es None, 'A' o 'B'. El estado raíz no
        necesita ser no terminal (si lo es, se devuelve acción None y su
        utilidad exacta).

    Postconditions:
        Devuelve un ResultadoDecision con la acción elegida (primera de las
        mejores según el orden determinista de `acciones_legales`), su valor
        Minimax desde la perspectiva de `bando_max` y las métricas congeladas.
        El valor NO es necesariamente la utilidad exacta de toda la partida:
        es exacto solo si dentro del horizonte se alcanza un estado terminal
        (victoria/derrota/empate); cuando la búsqueda llega al horizonte de
        profundidad, el valor de la raíz se calcula con la evaluación
        heurística de `utility.evaluar_estado`. No modifica `estado` ni
        `scenario`.

    Complexity:
        Tiempo: en el peor caso recorre O(b^d) nodos del árbol (b factor de
        ramificación, d profundidad), y el costo por nodo no es constante:
        cada nodo ejecuta `acciones_legales` y, por cada acción, aplicar
        acción, ambos O(U^2) en el motor de reglas. El factor b no se acota
        con 4*U: además de los movimientos ortogonales, las transferencias y
        las intercepciones añaden acciones legales.
        Espacio: O(d * b) adicional por la pila de recursión y las colecciones
        de acciones de cada nivel.

    """
    if bando_max is None:
        bando_max = estado.turno
    if bando_max not in ("A", "B"):
        raise ValueError("El bando MAX debe ser 'A' o 'B'.")

    niveles = profundidad_efectiva(scenario, profundidad)
    contador = ContadorMetricas()

    # La profundidad alcanzada arranca en 0 (raíz) en todos los casos,
    # incluido el de una raíz terminal.
    contador.registrar_profundidad(0)

    # 1) Raíz terminal: se comprueba explícitamente ANTES de pedir las
    #    acciones legales. La partida ya terminó: no hay acción posible
    #    (accion=None) y el valor es la utilidad exacta del estado.
    if resultado_partida(estado, scenario) is not None:
        contador.evaluados += 1
        return ResultadoDecision(
            accion=None,
            valor=evaluar_estado(estado, scenario, bando_max),
            metricas=contador.finalizar(),
        )

    # 2) Raíz no terminal: se expande y se aplica la selección Minimax.
    acciones = acciones_legales(estado, scenario)
    contador.expandidos += 1

    es_max = estado.turno == bando_max
    mejor_accion = None
    mejor_valor = None

    for accion in acciones:
        hijo = aplicar_accion(estado, accion, scenario)
        contador.generados += 1
        valor = _valor_minimax(
            hijo, scenario, bando_max, niveles - 1, 1, contador
        )
        # Mismo criterio de desempate que la recursión: estricto, primero gana.
        if mejor_valor is None or (es_max and valor > mejor_valor) or (
            (not es_max) and valor < mejor_valor
        ):
            mejor_valor = valor
            mejor_accion = accion

    return ResultadoDecision(
        accion=mejor_accion,
        valor=mejor_valor,
        metricas=contador.finalizar(),
    )
