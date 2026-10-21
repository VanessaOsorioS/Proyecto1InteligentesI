"""Partida automática: ambos bandos deciden con el mismo algoritmo.

Cada turno, el bando en turno elige una acción según el algoritmo seleccionado:

- Minimax y Alfa-Beta: decisión adversarial sobre el estado completo.
- BFS, DFS, UCS, A* y Beam: búsqueda de ruta para una unidad propia hacia su
  objetivo (base si es portador, recurso si nadie lo lleva, o el portador
  enemigo si lo tiene). Si hay una intercepción disponible se usa directamente.
  Si el portador propio está bloqueado, se evalúa transferir el recurso a un
  aliado adyacente con una ruta claramente mejor. La base propia admite varios
  aliados, así que no se descarta como meta cuando ya hay unidades del mismo
  bando. Si el primer paso devuelve a la unidad a la celda de la que viene, se
  replantea la ruta con el mismo algoritmo seleccionado, bloqueando esa celda,
  para evitar ciclos de dos posiciones sin mezclar algoritmos.

No conoce pygame: la UI sólo consume `avanzar`, `posiciones_previas` y `resumen`.
"""

import time
from dataclasses import dataclass, replace

from tacticalgrid.decision.alphabeta import poda_alfa_beta
from tacticalgrid.decision.minimax import minimax
from tacticalgrid.domain.actions import Accion, Interceptar, Mover, Transferir
from tacticalgrid.domain.position import Position
from tacticalgrid.domain.rules import (
    Resultado,
    acciones_legales,
    aplicar_accion,
    celdas_bloqueadas_para,
    resultado_partida,
)
from tacticalgrid.domain.scenario import Scenario
from tacticalgrid.domain.state import GameState
from tacticalgrid.domain.unit import Unit
from tacticalgrid.search.astar import buscar as astar
from tacticalgrid.search.beam import buscar as beam
from tacticalgrid.search.bfs import bfs
from tacticalgrid.search.dfs import dfs
from tacticalgrid.search.heuristics import (
    crear_distancia_exacta_multiple,
    crear_manhattan_multiple,
)
from tacticalgrid.search.problem import (
    ProblemaMultiobjetivo,
    ResultadoBusqueda,
    objetivos_adyacentes,
)
from tacticalgrid.search.ucs import ucs
from tacticalgrid.verification.verifiers import verificar_camino

ALGORITMOS_BUSQUEDA = (
    "BFS",
    "DFS",
    "UCS",
    "A*",
    "Beam k=1",
    "Beam k=2",
    "Beam k=4",
    "Beam k=8",
)
ALGORITMOS_DECISION = ("Minimax", "Alfa-Beta")
ALGORITMOS = ALGORITMOS_BUSQUEDA + ALGORITMOS_DECISION
HEURISTICAS = ("Manhattan", "Exacta")
HEURISTICA_POR_DEFECTO = "Manhattan"


@dataclass(frozen=True)
class RegistroBusqueda:
    """Datos estructurados de la búsqueda que decidió un movimiento.

    Attributes:
        unidad: Identificador de la unidad que buscó la ruta.
        exito: Si la búsqueda encontró camino.
        camino: Celdas (fila, columna) desde la posición actual hasta la meta.
        costo: Costo del camino encontrado.
        generados: Estados insertados en la frontera.
        expandidos: Estados expandidos.
        frontera_maxima: Mayor tamaño de la frontera.
        tiempo_ms: Tiempo total de la búsqueda en milisegundos.
    """

    unidad: str
    exito: bool
    camino: tuple[tuple[int, int], ...]
    costo: float
    generados: int
    expandidos: int
    frontera_maxima: int
    tiempo_ms: float


@dataclass(frozen=True)
class PasoPartida:
    """Registro de un turno ejecutado.

    Attributes:
        numero_turno: Número de turno en que se tomó la decisión.
        bando: Bando que jugó.
        descripcion: Texto legible de la acción.
        metricas: Resumen de la decisión (nodos, tiempo, etc.).
        busqueda: Datos de la búsqueda, o None si la acción no usó búsqueda.
        portador: Unidad que lleva el recurso tras la acción, o None.
        posicion_portador: Celda (fila, columna) del portador tras la acción.
    """

    numero_turno: int
    bando: str
    descripcion: str
    metricas: str
    busqueda: RegistroBusqueda | None = None
    portador: str | None = None
    posicion_portador: tuple[int, int] | None = None


def describir_accion(accion: Accion) -> str:
    """
    Purpose:
        Convertir una acción en texto legible para el panel.

    Preconditions:
        `accion` es una instancia de Accion.

    Postconditions:
        Devuelve una cadena. Para tipos desconocidos devuelve la representación.

    Complexity:
        O(1).

    AI usage: Yes
    AI intervention:
        Formateo de texto propuesto con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    if isinstance(accion, Mover):
        return f"{accion.unidad_id} -> fila {accion.destino.row}, col {accion.destino.column}"
    if isinstance(accion, Transferir):
        return f"{accion.origen_id} transfiere el recurso a {accion.destino_id}"
    if isinstance(accion, Interceptar):
        return f"{accion.unidad_id} intercepta el recurso"
    return "pasa el turno"


class Partida:
    """Partida en curso con decisión automática para ambos bandos.

    Attributes:
        scenario: Configuración estática del escenario.
        estado: Estado actual de la partida.
        algoritmo: Etiqueta del algoritmo que usan ambos bandos.
        heuristica: Heurística de búsqueda ('Manhattan' o 'Exacta') para A*/Beam.
        resultado: Resultado final o None si sigue en curso.
        historial: Lista de PasoPartida ejecutados.
        _posicion_previa: Posición que ocupaba cada unidad antes de su última
            acción de movimiento.
    """

    def __init__(
        self,
        scenario: Scenario,
        estado: GameState,
        algoritmo: str,
        heuristica: str = HEURISTICA_POR_DEFECTO,
    ):
        """
        Purpose:
            Crear una partida lista para ejecutar turnos.

        Preconditions:
            `scenario` y `estado` son coherentes; `algoritmo` está en ALGORITMOS;
            `heuristica` está en HEURISTICAS.

        Postconditions:
            Lanza ValueError si el algoritmo o la heurística no existen. Guarda la
            heurística aunque el algoritmo no la use. No ejecuta ningún turno.

        Complexity:
            O(T), donde T es el número de tipos de terreno.

        AI usage: Yes
        AI intervention:
            Clase propuesta con asistencia de IA.
        Student validation:
            Pendiente de ejecución y validación del equipo.
        """
        if algoritmo not in ALGORITMOS:
            raise ValueError(f"Algoritmo desconocido: '{algoritmo}'.")

        if heuristica not in HEURISTICAS:
            raise ValueError(f"Heurística desconocida: '{heuristica}'.")

        self.scenario = scenario
        self.estado = estado
        self.algoritmo = algoritmo
        self.heuristica = heuristica
        self.anterior: GameState | None = None
        self.resultado: Resultado | None = resultado_partida(estado, scenario)
        self.historial: list[PasoPartida] = []
        self._posicion_previa: dict[str, Position] = {}
        self._ultima_busqueda: tuple[ResultadoBusqueda, str] | None = None
        self._costo_minimo = min(
            (
                terreno.cost
                for terreno in scenario.tablero.terrain_types.values()
                if terreno.walkable
            ),
            default=1,
        )

    @property
    def terminada(self) -> bool:
        """Indica si la partida ya tiene resultado."""
        return self.resultado is not None

    def avanzar(self) -> PasoPartida | None:
        """
        Purpose:
            Ejecutar un turno: decidir la acción del bando en turno y aplicarla.

        Preconditions:
            La partida no ha terminado.

        Postconditions:
            Actualiza `estado`, `anterior`, `resultado` e `historial`. Devuelve
            el PasoPartida ejecutado, o None si la partida ya había terminado.

        Complexity:
            Depende del algoritmo: en Minimax/Alfa-Beta O(b^d) nodos; en búsqueda
            O(U * (V + E)) para U unidades propias.

        AI usage: Yes
        AI intervention:
            Bucle de turnos propuesto con asistencia de IA.
        Student validation:
            Pendiente de ejecución y validación del equipo.
        """
        if self.terminada:
            return None

        estado = self.estado
        self._ultima_busqueda = None
        accion, texto = self._decidir(estado)
        busqueda = self._ultima_busqueda
        posiciones_antes = {
            unidad.id: unidad.posicion for unidad in estado.unidades
        }
        siguiente = aplicar_accion(estado, accion, self.scenario)

        if isinstance(accion, Mover):
            self._posicion_previa[accion.unidad_id] = posiciones_antes[
                accion.unidad_id
            ]

        portador = siguiente.unidad(siguiente.portador) if siguiente.portador else None
        registro = None
        if busqueda is not None:
            resultado, unidad_id = busqueda
            m = resultado.metricas
            registro = RegistroBusqueda(
                unidad=unidad_id,
                exito=resultado.exito,
                camino=tuple(
                    (celda.row, celda.column) for celda in resultado.camino
                ),
                costo=float(resultado.costo),
                generados=m.generados,
                expandidos=m.expandidos,
                frontera_maxima=m.frontera_maxima,
                tiempo_ms=m.tiempo_segundos * 1000,
            )

        paso = PasoPartida(
            numero_turno=estado.numero_turno,
            bando=estado.turno,
            descripcion=describir_accion(accion),
            metricas=texto,
            busqueda=registro,
            portador=portador.id if portador else None,
            posicion_portador=(
                (portador.posicion.row, portador.posicion.column)
                if portador
                else None
            ),
        )

        self.anterior = estado
        self.estado = siguiente
        self.resultado = resultado_partida(siguiente, self.scenario)
        self.historial.append(paso)
        return paso

    def informe(self) -> dict:
        """
        Purpose:
            Resumir la partida en la estructura de comparación de algoritmos:
            resultado, camino del recurso y métricas de búsqueda acumuladas.

        Preconditions:
            Ninguna; funciona con la partida en curso o terminada.

        Postconditions:
            Devuelve un dict con 'algoritmo', 'exito' (victoria de un bando),
            'resultado', 'camino' (celdas por las que pasó el portador del
            recurso, sin repetir celdas consecutivas), 'costo' (suma de costos
            de las rutas planificadas), 'estados_generados', 'estados_expandidos',
            'maximo_frontera' y 'turnos' (detalle por turno con búsqueda). No
            modifica la partida.

        Complexity:
            O(T), donde T es el número de turnos ejecutados.

        AI usage: Yes
        AI intervention:
            Agregación de métricas para el informe propuesta con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        camino: list[list[int]] = []
        for paso in self.historial:
            if paso.posicion_portador is None:
                continue
            celda = list(paso.posicion_portador)
            if not camino or camino[-1] != celda:
                camino.append(celda)

        turnos = []
        generados = expandidos = frontera = 0
        costo = 0.0
        for paso in self.historial:
            b = paso.busqueda
            if b is None:
                continue
            generados += b.generados
            expandidos += b.expandidos
            frontera = max(frontera, b.frontera_maxima)
            costo += b.costo
            turnos.append(
                {
                    "turno": paso.numero_turno,
                    "bando": paso.bando,
                    "unidad": b.unidad,
                    "exito": b.exito,
                    "costo": b.costo,
                    "estados_generados": b.generados,
                    "estados_expandidos": b.expandidos,
                    "maximo_frontera": b.frontera_maxima,
                    "tiempo_ms": round(b.tiempo_ms, 2),
                }
            )

        resultado = self.resultado
        return {
            "algoritmo": self.algoritmo,
            "heuristica": self.heuristica,
            "exito": bool(resultado and resultado.ganador is not None),
            "resultado": {
                "ganador": resultado.ganador if resultado else None,
                "motivo": resultado.motivo if resultado else None,
                "turnos": len(self.historial),
            },
            "camino": camino,
            "costo": costo,
            "estados_generados": generados,
            "estados_expandidos": expandidos,
            "maximo_frontera": frontera,
            "turnos": turnos,
        }

    def posiciones_previas(self) -> dict[str, tuple[int, int]]:
        """Devuelve la posición de cada unidad antes del último turno (para animar)."""
        if self.anterior is None:
            return {}
        return {
            unidad.id: (unidad.posicion.row, unidad.posicion.column)
            for unidad in self.anterior.unidades
        }

    def resumen(self) -> list[str]:
        """Líneas de texto con el estado de la partida para el panel lateral."""
        lineas = []
        if self.terminada:
            lineas.append("Partida terminada")
            if self.resultado.ganador is None:
                lineas.append("Resultado: empate")
            else:
                lineas.append(f"Ganador: bando {self.resultado.ganador}")
            lineas.append(f"Motivo: {self.resultado.motivo}")
        else:
            lineas.append(
                f"Turno {self.estado.numero_turno}: juega bando {self.estado.turno}"
            )
            if self.estado.turnos_robo_bloqueado > 0:
                lineas.append(
                    f"Robo bloqueado: "
                    f"{self.estado.turnos_robo_bloqueado} turno(s)"
                )

        if self.historial:
            ultimo = self.historial[-1]
            lineas.append(f"Accion: {ultimo.bando}: {ultimo.descripcion}")
            lineas.append(f"Decision: {ultimo.metricas}")
        return lineas

    def _decidir(self, estado: GameState) -> tuple[Accion, str]:
        """Elige la acción del bando en turno según el algoritmo activo."""
        if self.algoritmo in ALGORITMOS_DECISION:
            funcion = minimax if self.algoritmo == "Minimax" else poda_alfa_beta
            resultado = funcion(estado, self.scenario)
            if resultado.accion is None:
                raise RuntimeError("El algoritmo no devolvió acción en una partida activa.")
            m = resultado.metricas
            texto = (
                f"gen {m.generados}, eval {m.evaluados}, podas {m.hijos_podados}, "
                f"prof {m.profundidad_alcanzada}, {m.tiempo_segundos * 1000:.0f} ms, "
                f"valor {resultado.valor:g}"
            )
            return resultado.accion, texto

        return self._decidir_busqueda(estado)

    def _decidir_busqueda(self, estado: GameState) -> tuple[Accion, str]:
        """
        Purpose:
            Elegir la acción del bando en turno usando solo el algoritmo de
            búsqueda seleccionado.

        Preconditions:
            `estado` es válido y la partida sigue activa.

        Postconditions:
            Devuelve una intercepción directa, una transferencia beneficiosa o
            un movimiento. Si ninguna unidad tiene ruta, intenta despejar la
            ruta del portador y, en último caso, una acción legal de respaldo.

        Complexity:
            O(U * S + A * S + M * S), donde U es el número de unidades propias,
            A el de aliados adyacentes, M el de movimientos legales y S el costo
            del algoritmo de búsqueda seleccionado.

        AI usage: Yes
        AI intervention:
            Selección de acciones y transferencia propuesta con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        legales = acciones_legales(estado, self.scenario)

        for accion in legales:
            if isinstance(accion, Interceptar):
                return accion, "intercepción directa (sin búsqueda)"

        transferencia = self._transferencia_conveniente(estado, legales)
        if transferencia is not None:
            return transferencia

        mejor: tuple[
            ResultadoBusqueda, Unit, tuple[Position, ...], frozenset[Position]
        ] | None = None
        for unidad in estado.unidades_de(estado.turno):
            bloqueadas = celdas_bloqueadas_para(estado, self.scenario, unidad)
            # Una meta bloqueada no es alcanzable; los aliados en la base
            # propia no bloquean.
            objetivos = tuple(
                meta
                for meta in self._objetivos(estado, unidad)
                if meta not in bloqueadas
            )
            if not objetivos:
                continue

            problema = ProblemaMultiobjetivo(
                self.scenario.tablero, unidad.posicion, objetivos, bloqueadas
            )
            resultado = self._buscar(problema, objetivos)
            verificar_camino(problema, resultado)

            # Un camino de longitud 0 significa que la unidad ya está en la meta.
            if not resultado.exito or resultado.longitud == 0:
                continue
            if mejor is None or resultado.costo < mejor[0].costo:
                mejor = (resultado, unidad, objetivos, bloqueadas)

        if mejor is None:
            despeje = self._despejar_ruta_portador(estado, legales)
            if despeje is not None:
                return despeje
            alternativa = self._movimiento_sin_retroceso(legales)
            if alternativa is not None:
                return alternativa, "sin ruta: movimiento alternativo"
            return legales[0], "sin ruta: acción por defecto"

        resultado, unidad, objetivos, bloqueadas = mejor
        destino = resultado.camino[1]
        anterior = self._posicion_previa.get(unidad.id)
        if anterior is not None and destino == anterior and anterior not in objetivos:
            alternativa = self._ruta_sin_retroceso(unidad, objetivos, bloqueadas)
            if alternativa is not None:
                resultado = alternativa
                destino = alternativa.camino[1]

        self._ultima_busqueda = (resultado, unidad.id)
        m = resultado.metricas
        texto = (
            f"{unidad.id}: costo {resultado.costo:g}, gen {m.generados}, "
            f"exp {m.expandidos}, {m.tiempo_segundos * 1000:.1f} ms, "
            f"h {self.heuristica}"
        )
        return Mover(unidad.id, destino), texto

    def _transferencia_conveniente(
        self, estado: GameState, legales: tuple[Accion, ...]
    ) -> tuple[Transferir, str] | None:
        """
        Purpose:
            Decidir si el portador debe entregar el recurso a un aliado adyacente
            con una ruta claramente mejor hacia la base.

        Preconditions:
            `estado` es válido; `legales` son las acciones del bando en turno.

        Postconditions:
            Devuelve `(Transferir, texto)` si conviene transferir; `None` en caso
            contrario. La comparación usa turnos: ruta del aliado + 1 turno de
            transferencia debe ser estrictamente menor que la ruta del portador.
            Si el portador no tiene ruta y el aliado sí, se transfiere.

        Complexity:
            O((A + 1) * S), donde A es el número de aliados adyacentes y S el
            costo del algoritmo de búsqueda seleccionado.

        AI usage: Yes
        AI intervention:
            Criterio de transferencia por turnos propuesto con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        if estado.portador is None:
            return None

        portador = estado.unidad(estado.portador)
        if portador is None or portador.bando != estado.turno:
            return None

        base = self.scenario.bases[portador.bando]
        longitud_portador, _ = self._longitud_hasta_base(estado, portador, base)
        mejor: tuple[float, str, Transferir, float] | None = None

        for accion in legales:
            if not isinstance(accion, Transferir):
                continue
            if accion.origen_id != portador.id:
                continue

            aliado = estado.unidad(accion.destino_id)
            if aliado is None:
                continue

            longitud_aliado, _ = self._longitud_hasta_base(estado, aliado, base)
            if aliado.posicion == base:
                return accion, f"transferencia a {aliado.id}: llega a la base"
            if longitud_aliado == float("inf"):
                continue

            efectivo = longitud_aliado + 1.0
            if efectivo >= longitud_portador:
                continue
            if mejor is None or (efectivo, aliado.id) < (mejor[0], mejor[1]):
                mejor = (efectivo, aliado.id, accion, longitud_aliado)

        if mejor is None:
            return None

        _, _, accion, longitud_aliado = mejor
        if longitud_portador == float("inf"):
            texto = (
                f"transferencia a {accion.destino_id}: "
                f"{longitud_aliado:g} pasos; portador sin ruta"
            )
        else:
            texto = (
                f"transferencia a {accion.destino_id}: "
                f"{longitud_aliado:g} pasos + 1 turno < "
                f"{longitud_portador:g} del portador"
            )
        return accion, texto

    def _longitud_hasta_base(
        self, estado: GameState, unidad: Unit, base: Position
    ) -> tuple[float, ResultadoBusqueda | None]:
        """
        Purpose:
            Calcular la longitud de la ruta de una unidad hasta su base con el
            algoritmo de búsqueda seleccionado.

        Preconditions:
            `estado` es válido; `unidad` pertenece al estado; `base` es la base
            de su bando.

        Postconditions:
            Devuelve `(0, None)` si la unidad ya está en la base,
            `(inf, None)` si la base está bloqueada (por ejemplo, por un
            enemigo), o la longitud de la ruta y el resultado de búsqueda. Los
            aliados en la base propia no bloquean. Si no hay ruta, la longitud
            es infinita.

        Complexity:
            O(S), donde S es el costo del algoritmo de búsqueda seleccionado.

        AI usage: Yes
        AI intervention:
            Medición de rutas para transferencias propuesta con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        if unidad.posicion == base:
            return 0.0, None

        bloqueadas = celdas_bloqueadas_para(estado, self.scenario, unidad)
        if base in bloqueadas:
            return float("inf"), None

        problema = ProblemaMultiobjetivo(
            self.scenario.tablero, unidad.posicion, (base,), bloqueadas
        )
        resultado = self._buscar(problema, (base,))
        verificar_camino(problema, resultado)
        if not resultado.exito:
            return float("inf"), resultado
        return float(resultado.longitud), resultado

    def _ruta_sin_retroceso(
        self,
        unidad: Unit,
        objetivos: tuple[Position, ...],
        bloqueadas: frozenset[Position],
    ) -> ResultadoBusqueda | None:
        """
        Purpose:
            Replantear la ruta de una unidad bloqueando su celda anterior, para
            evitar que el camino calculado la devuelva al punto de partida.

        Preconditions:
            `unidad` pertenece al bando en turno; `objetivos` no está vacío;
            `bloqueadas` contiene las posiciones ocupadas por las demás unidades.

        Postconditions:
            Devuelve una ruta alternativa usando el algoritmo seleccionado, o
            `None` si no existe. No modifica el estado.

        Complexity:
            O(S), donde S es el costo del algoritmo de búsqueda seleccionado.

        AI usage: Yes
        AI intervention:
            Estrategia anti-oscilación propuesta con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        anterior = self._posicion_previa.get(unidad.id)
        if anterior is None or anterior in objetivos:
            return None

        problema = ProblemaMultiobjetivo(
            self.scenario.tablero,
            unidad.posicion,
            objetivos,
            bloqueadas | {anterior},
        )
        resultado = self._buscar(problema, objetivos)
        verificar_camino(problema, resultado)
        if not resultado.exito or resultado.longitud == 0:
            return None
        return resultado

    def _despejar_ruta_portador(
        self, estado: GameState, legales: tuple[Accion, ...]
    ) -> tuple[Mover, str] | None:
        """
        Purpose:
            Buscar un movimiento propio que abra una ruta para el portador
            cuando ninguna unidad tiene camino disponible.

        Preconditions:
            `estado` es válido; `legales` son las acciones del bando en turno.

        Postconditions:
            Devuelve `(Mover, texto)` para el movimiento que minimiza la ruta del
            portador, o `None` si ningún movimiento legal le abre una ruta. Usa
            el algoritmo de búsqueda seleccionado.

        Complexity:
            O(M * S), donde M es el número de movimientos legales y S el costo
            del algoritmo de búsqueda seleccionado.

        AI usage: Yes
        AI intervention:
            Desempate por despeje de ruta propuesto con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        if estado.portador is None:
            return None

        portador = estado.unidad(estado.portador)
        if portador is None or portador.bando != estado.turno:
            return None

        base = self.scenario.bases[portador.bando]
        mejor: tuple[tuple[float, str, int, int], Mover, int] | None = None

        for accion in legales:
            if not isinstance(accion, Mover):
                continue

            unidades = tuple(
                Unit(unidad.id, unidad.bando, unidad.tipo, accion.destino)
                if unidad.id == accion.unidad_id
                else unidad
                for unidad in estado.unidades
            )
            portador_simulado = next(
                unidad for unidad in unidades if unidad.id == portador.id
            )
            if portador_simulado.posicion == base:
                return accion, f"{accion.unidad_id}: entra a la base"

            bloqueadas = celdas_bloqueadas_para(
                estado, self.scenario, portador_simulado, unidades
            )
            if base in bloqueadas:
                continue

            problema = ProblemaMultiobjetivo(
                self.scenario.tablero,
                portador_simulado.posicion,
                (base,),
                bloqueadas,
            )
            resultado = self._buscar(problema, (base,))
            verificar_camino(problema, resultado)
            if not resultado.exito or resultado.longitud == 0:
                continue

            clave = (
                float(resultado.longitud),
                accion.unidad_id,
                accion.destino.row,
                accion.destino.column,
            )
            if mejor is None or clave < mejor[0]:
                mejor = (clave, accion, resultado.longitud)

        if mejor is None:
            return None

        _, accion, longitud = mejor
        return accion, (
            f"{accion.unidad_id}: despeja la ruta del portador "
            f"({longitud} pasos)"
        )

    def _movimiento_sin_retroceso(
        self, legales: tuple[Accion, ...]
    ) -> Mover | None:
        """
        Purpose:
            Elegir un movimiento legal que no devuelva a una unidad a la celda
            desde la que acaba de llegar.

        Preconditions:
            `legales` son las acciones del bando en turno.

        Postconditions:
            Devuelve el primer `Mover` que no sea un retroceso inmediato, o
            `None` si todos los movimientos legales lo son.

        Complexity:
            O(M), donde M es el número de acciones legales.

        AI usage: Yes
        AI intervention:
            Regla de respaldo anti-repetición propuesta con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        for accion in legales:
            if not isinstance(accion, Mover):
                continue
            if self._posicion_previa.get(accion.unidad_id) == accion.destino:
                continue
            return accion
        return None

    def _objetivos(self, estado: GameState, unidad: Unit) -> tuple:
        """
        Purpose:
            Calcular las celdas meta de una unidad propia según la situación.

        Preconditions:
            `estado` es válido; `unidad` pertenece al bando en turno.

        Postconditions:
            Devuelve la base propia si la unidad es portadora; las celdas
            adyacentes al portador enemigo si el recurso lo lleva el rival; o
            la celda del recurso si nadie lo transporta. Para un aliado del
            portador devuelve una tupla vacía.

        Complexity:
            O(U), donde U es el número de unidades.

        AI usage: No
        AI intervention:
            Ninguna.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        bando = unidad.bando
        tablero = self.scenario.tablero
        bloqueadas = celdas_bloqueadas_para(estado, self.scenario, unidad)
        portador = estado.unidad(estado.portador) if estado.portador is not None else None

        if portador is not None and portador.bando == bando:
            # Solo el portador tiene meta (su base); el resto no tiene objetivo.
            if portador.id == unidad.id:
                return (self.scenario.bases[bando],)
            return ()

        if portador is not None:
            # Portador enemigo: acercarse para interceptar.
            return objetivos_adyacentes(tablero, portador.posicion, bloqueadas)

        return (self.scenario.recurso,)

    def _buscar(self, problema: ProblemaMultiobjetivo, objetivos) -> ResultadoBusqueda:
        """
        Purpose:
            Ejecutar el algoritmo de búsqueda seleccionado sobre el problema,
            usando la heurística configurada en A* y Beam.

        Preconditions:
            `problema` es coherente con `objetivos`; la partida está activa.

        Postconditions:
            Devuelve el resultado del algoritmo. En A* y Beam registra en las
            métricas el tiempo de construcción de la heurística (Manhattan o
            distancia exacta). En BFS, DFS y UCS esa métrica queda en 0.0.

        Complexity:
            La del algoritmo seleccionado; la distancia exacta añade una
            construcción O(F*C*log(F*C)) antes de A* o Beam.

        AI usage: Yes
        AI intervention:
            Selección de heurística propuesta con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        nombre = self.algoritmo
        if nombre == "BFS":
            return bfs(problema)
        if nombre == "DFS":
            return dfs(problema)
        if nombre == "UCS":
            return ucs(problema)

        inicio_heuristica = time.perf_counter()
        if self.heuristica == "Exacta":
            heuristica = crear_distancia_exacta_multiple(
                problema.tablero, objetivos, problema.bloqueadas
            )
        else:
            heuristica = crear_manhattan_multiple(objetivos, self._costo_minimo)
        tiempo_heuristica = time.perf_counter() - inicio_heuristica

        if nombre == "A*":
            resultado = astar(problema, heuristica)
        else:
            ancho = int(nombre.split("k=")[1])
            resultado = beam(problema, heuristica, ancho)

        return ResultadoBusqueda(
            camino=resultado.camino,
            costo=resultado.costo,
            exito=resultado.exito,
            metricas=replace(
                resultado.metricas,
                tiempo_heuristica_segundos=tiempo_heuristica,
            ),
        )
