"""Partida automática: ambos bandos deciden con el mismo algoritmo.

Cada turno, el bando en turno elige una acción según el algoritmo seleccionado:

- Minimax y Alfa-Beta: decisión adversarial sobre el estado completo.
- BFS, DFS, UCS, A* y Beam: búsqueda de ruta para una unidad propia hacia su
  objetivo (base si es portador, recurso si nadie lo lleva, o el portador
  enemigo si lo tiene). Si hay una intercepción disponible se usa directamente.
  Si el primer paso devuelve a la unidad a la celda de la que viene, se compara
  el costo exacto restante de las celdas legales (incluida la previa) y se
  prefiere no retroceder para evitar ciclos de dos posiciones.

No conoce pygame: la UI sólo consume `avanzar`, `posiciones_previas` y `resumen`.
"""

from dataclasses import dataclass

from tacticalgrid.decision.alphabeta import poda_alfa_beta
from tacticalgrid.decision.minimax import minimax
from tacticalgrid.domain.actions import Accion, Interceptar, Mover, Transferir
from tacticalgrid.domain.position import Position
from tacticalgrid.domain.rules import (
    Resultado,
    acciones_legales,
    aplicar_accion,
    resultado_partida,
)
from tacticalgrid.domain.scenario import Scenario
from tacticalgrid.domain.state import GameState
from tacticalgrid.domain.unit import Unit
from tacticalgrid.search.astar import buscar as astar
from tacticalgrid.search.beam import buscar as beam
from tacticalgrid.search.bfs import bfs
from tacticalgrid.search.dfs import dfs
from tacticalgrid.search.heuristics import crear_manhattan_multiple
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


@dataclass(frozen=True)
class PasoPartida:
    """Registro de un turno ejecutado.

    Attributes:
        numero_turno: Número de turno en que se tomó la decisión.
        bando: Bando que jugó.
        descripcion: Texto legible de la acción.
        metricas: Resumen de la decisión (nodos, tiempo, etc.).
    """

    numero_turno: int
    bando: str
    descripcion: str
    metricas: str


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
        resultado: Resultado final o None si sigue en curso.
        historial: Lista de PasoPartida ejecutados.
        _posicion_previa: Posición que ocupaba cada unidad antes de su última
            acción de movimiento.
    """

    def __init__(self, scenario: Scenario, estado: GameState, algoritmo: str):
        """
        Purpose:
            Crear una partida lista para ejecutar turnos.

        Preconditions:
            `scenario` y `estado` son coherentes; `algoritmo` está en ALGORITMOS.

        Postconditions:
            Lanza ValueError si el algoritmo no existe. No ejecuta ningún turno.

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

        self.scenario = scenario
        self.estado = estado
        self.algoritmo = algoritmo
        self.anterior: GameState | None = None
        self.resultado: Resultado | None = resultado_partida(estado, scenario)
        self.historial: list[PasoPartida] = []
        self._posicion_previa: dict[str, Position] = {}
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
        accion, texto = self._decidir(estado)
        posiciones_antes = {
            unidad.id: unidad.posicion for unidad in estado.unidades
        }
        siguiente = aplicar_accion(estado, accion, self.scenario)

        if isinstance(accion, Mover):
            self._posicion_previa[accion.unidad_id] = posiciones_antes[
                accion.unidad_id
            ]

        paso = PasoPartida(
            numero_turno=estado.numero_turno,
            bando=estado.turno,
            descripcion=describir_accion(accion),
            metricas=texto,
        )

        self.anterior = estado
        self.estado = siguiente
        self.resultado = resultado_partida(siguiente, self.scenario)
        self.historial.append(paso)
        return paso

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
        """Elige la unidad propia con la ruta de menor costo hacia su objetivo."""
        legales = acciones_legales(estado, self.scenario)

        for accion in legales:
            if isinstance(accion, Interceptar):
                return accion, "intercepción directa (sin búsqueda)"

        mejor: tuple[
            ResultadoBusqueda, Unit, tuple[Position, ...], frozenset[Position]
        ] | None = None
        for unidad in estado.unidades_de(estado.turno):
            bloqueadas = frozenset(
                otra.posicion for otra in estado.unidades if otra.id != unidad.id
            )
            # Una meta ocupada por otra unidad no es alcanzable: se descarta.
            objetivos = tuple(
                meta for meta in self._objetivos(estado, unidad) if meta not in bloqueadas
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
            # Sin ruta disponible para ninguna unidad: primera acción legal.
            return legales[0], "sin ruta: acción por defecto"

        resultado, unidad, objetivos, bloqueadas = mejor
        destino = self._paso_sin_retroceso(
            estado, unidad, resultado.camino[1], objetivos, bloqueadas
        )
        m = resultado.metricas
        texto = (
            f"{unidad.id}: costo {resultado.costo:g}, gen {m.generados}, "
            f"exp {m.expandidos}, {m.tiempo_segundos * 1000:.1f} ms"
        )
        return Mover(unidad.id, destino), texto

    def _paso_sin_retroceso(
        self,
        estado: GameState,
        unidad: Unit,
        destino: Position,
        objetivos: tuple[Position, ...],
        bloqueadas: frozenset[Position],
    ) -> Position:
        """
        Purpose:
            Evitar que una unidad repita en su siguiente movimiento la celda
            desde la que acaba de llegar, cuando el camino calculado la devuelve
            a ella.

        Preconditions:
            `estado` es válido; `unidad` pertenece al bando en turno; `destino`
            es una celda legal del camino calculado; `objetivos` no está vacío;
            `bloqueadas` contiene las posiciones ocupadas por las demás unidades.

        Postconditions:
            Devuelve `destino` si no es la posición previa de la unidad. En caso
            contrario compara todas las celdas legales, incluida la previa, por
            costo exacto restante hacia los objetivos y devuelve la de menor
            costo; ante empate prefiere no retroceder. Si ninguna tiene ruta,
            devuelve `destino`.

        Complexity:
            O(k * (V + E) log V), con k <= 4 celdas legales; V y E son las
            celdas y conexiones transitables del tablero.

        AI usage: Yes
        AI intervention:
            Estrategia anti-oscilación propuesta con asistencia de IA.
        Student validation:
            Pendiente de revisión por el equipo.
        """
        anterior = self._posicion_previa.get(unidad.id)
        if anterior is None or destino != anterior:
            return destino

        candidatos = [
            accion.destino
            for accion in acciones_legales(estado, self.scenario)
            if isinstance(accion, Mover) and accion.unidad_id == unidad.id
        ]
        if not candidatos:
            return destino

        mejor_destino = destino
        mejor_clave: tuple[float, bool, int, int] | None = None
        for candidato in candidatos:
            problema = ProblemaMultiobjetivo(
                self.scenario.tablero, candidato, objetivos, bloqueadas
            )
            resultado = ucs(problema)
            if not resultado.exito:
                continue
            clave = (
                resultado.costo,
                candidato == anterior,
                candidato.row,
                candidato.column,
            )
            if mejor_clave is None or clave < mejor_clave:
                mejor_clave = clave
                mejor_destino = candidato

        return mejor_destino

    def _objetivos(self, estado: GameState, unidad: Unit) -> tuple:
        """Calcula las celdas meta de una unidad propia según la situación."""
        bando = unidad.bando
        tablero = self.scenario.tablero
        ocupadas = frozenset(otra.posicion for otra in estado.unidades)
        portador = estado.unidad(estado.portador) if estado.portador is not None else None

        if portador is not None and portador.bando == bando:
            # Solo el portador tiene meta (su base); el resto no tiene objetivo.
            if portador.id == unidad.id:
                return (self.scenario.bases[bando],)
            return ()

        if portador is not None:
            # Portador enemigo: acercarse para interceptar.
            return objetivos_adyacentes(tablero, portador.posicion, ocupadas)

        return (self.scenario.recurso,)

    def _buscar(self, problema: ProblemaMultiobjetivo, objetivos) -> ResultadoBusqueda:
        """Ejecuta el algoritmo de búsqueda seleccionado sobre el problema."""
        nombre = self.algoritmo
        if nombre == "BFS":
            return bfs(problema)
        if nombre == "DFS":
            return dfs(problema)
        if nombre == "UCS":
            return ucs(problema)

        heuristica = crear_manhattan_multiple(objetivos, self._costo_minimo)
        if nombre == "A*":
            return astar(problema, heuristica)

        ancho = int(nombre.split("k=")[1])
        return beam(problema, heuristica, ancho)
