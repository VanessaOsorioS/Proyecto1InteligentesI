from tacticalgrid.decision.minimax import profundidad_efectiva
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

INF = float("inf")


def _valor_poda(
    estado: GameState,
    scenario: Scenario,
    bando_max: str,
    restante: int,
    nivel: int,
    alfa: float,
    beta: float,
    contador: ContadorMetricas,
) -> float:
    """Valor Minimax de `estado` con poda alfa-beta (recursión)."""
    contador.registrar_profundidad(nivel)

    # Hoja: estado terminal o profundidad agotada -> función de utilidad.
    if resultado_partida(estado, scenario) is not None or restante == 0:
        contador.evaluados += 1
        return evaluar_estado(estado, scenario, bando_max)

    acciones = acciones_legales(estado, scenario)
    contador.expandidos += 1

    es_max = estado.turno == bando_max

    mejor = None
    for indice, accion in enumerate(acciones):
        hijo = aplicar_accion(estado, accion, scenario)
        contador.generados += 1
        valor_hijo = _valor_poda(
            hijo, scenario, bando_max, restante - 1, nivel + 1, alfa, beta, contador
        )

        # Comparación estricta: en empates se conserva la primera acción
        # (mismo criterio que Minimax para garantizar la misma elección).
        if mejor is None or (es_max and valor_hijo > mejor) or (
            (not es_max) and valor_hijo < mejor
        ):
            mejor = valor_hijo
            if es_max:
                alfa = max(alfa, mejor)
            else:
                beta = min(beta, mejor)

        # Corte: la ventana se cerró (alfa >= beta) y este nodo ya no puede
        # mejorar el resultado del padre. Solo se registra una poda EFECTIVA:
        # si no quedan acciones hermanas sin explorar (restantes == 0), el
        # corte no descarta nada y no se contabiliza.
        if alfa >= beta:
            restantes = len(acciones) - (indice + 1)
            if restantes > 0:
                contador.cortes += 1
                contador.hijos_podados += restantes
            break

    if mejor is None:
        # Inalcanzable: si el estado no es terminal, siempre hay al menos una
        # acción (Pasar es legal cuando no hay otra). Se deja constancia.
        contador.evaluados += 1
        return evaluar_estado(estado, scenario, bando_max)

    return mejor


def poda_alfa_beta(
    estado: GameState,
    scenario: Scenario,
    profundidad: int | None = None,
    bando_max: str | None = None,
) -> ResultadoDecision:
    """
    Purpose:
        Elegir la acción del bando en turno (o de `bando_max`) mediante
        Minimax con poda alfa-beta.

    Preconditions:
        `estado` y `scenario` son válidos y coherentes; `profundidad` es None o
        un entero positivo; `bando_max` es None, 'A' o 'B'. El estado raíz no
        necesita ser no terminal (si lo es, se devuelve acción None y su
        utilidad exacta).

    Postconditions:
        Devuelve un ResultadoDecision con la acción elegida y su valor Minimax,
        idénticos a los de `minimax.minimax` con los mismos argumentos (la poda
        no altera la calidad de la decisión). El valor corresponde a Minimax
        dentro del horizonte configurado: las hojas usan utilidades terminales
        exactas y evaluaciones heurísticas (`utility.evaluar_estado`). El hecho
        de que alguna rama alcance un estado terminal NO implica que el valor
        de la raíz sea la utilidad exacta de la partida; solo refleja la mejor
        línea de juego dentro del límite de profundidad. Las métricas
        registran `cortes` e `hijos_podados` solo cuando hay poda efectiva
        (quedaban hermanos sin explorar). Los hijos podados nunca se evalúan:
        no se usan sus valores como cotas de decisión. No modifica `estado`
        ni `scenario`.

    Complexity:
        Tiempo: en el peor caso O(b^d) nodos del árbol (b factor de
        ramificación, d profundidad), igual que Minimax; O(b^(d/2)) en el
        mejor caso con orden ideal de acciones. El costo por nodo no es
        constante: cada nodo ejecuta `acciones_legales` y, por cada acción,
        `aplicar_accion`, ambos O(U^2) en el motor de reglas. El factor b no
        se acota con 4*U: además de los movimientos ortogonales, las
        transferencias y las intercepciones añaden acciones legales.
        Espacio: O(d * b) adicional por la pila de recursión y las colecciones
        de acciones de cada nivel. Los hijos podados no se expanden, lo que
        reduce el número real de nodos explorados.

    Student validation:
        Pendiente de ejecución y validación del equipo.

    AI usage: Yes
    AI intervention:
        Algoritmo implementado con asistencia de IA (guía del plan aprobado
        por el equipo).
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

    # 2) Raíz no terminal: se expande y se aplica la selección con poda.
    acciones = acciones_legales(estado, scenario)
    contador.expandidos += 1

    es_max = estado.turno == bando_max
    alfa, beta = -INF, INF
    mejor_accion = None
    mejor_valor = None

    for indice, accion in enumerate(acciones):
        hijo = aplicar_accion(estado, accion, scenario)
        contador.generados += 1
        valor = _valor_poda(
            hijo, scenario, bando_max, niveles - 1, 1, alfa, beta, contador
        )
        # Mismo criterio de desempate que Minimax: estricto, primero gana.
        if mejor_valor is None or (es_max and valor > mejor_valor) or (
            (not es_max) and valor < mejor_valor
        ):
            mejor_valor = valor
            mejor_accion = accion
            if es_max:
                alfa = max(alfa, mejor_valor)
            else:
                beta = min(beta, mejor_valor)

        # Corte en la raíz: los hermanos restantes no cambian la decisión.
        # Misma convención que en _valor_poda: poda efectiva solo si quedan
        # acciones hermanas sin explorar.
        if alfa >= beta:
            restantes = len(acciones) - (indice + 1)
            if restantes > 0:
                contador.cortes += 1
                contador.hijos_podados += restantes
            break

    return ResultadoDecision(
        accion=mejor_accion,
        valor=mejor_valor,
        metricas=contador.finalizar(),
    )
