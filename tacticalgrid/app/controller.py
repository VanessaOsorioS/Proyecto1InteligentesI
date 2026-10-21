"""Orquestación entre la capa de E/S y la interfaz gráfica.

Transforma el diccionario validado que devuelve `load_scenario` en un modelo de
vista listo para dibujar, reutilizando la clase `Board` del dominio para validar
la coherencia del tablero.
"""

from dataclasses import dataclass, replace

from tacticalgrid.app.partida import (
    ALGORITMOS_BUSQUEDA,
    HEURISTICA_POR_DEFECTO,
    HEURISTICAS,
    Partida,
)
from tacticalgrid.domain.board import Board
from tacticalgrid.domain.state import GameState
from tacticalgrid.domain.terrain import Terrain
from tacticalgrid.io.scenario_loader import cargar_modelo, load_scenario

ALGORITMOS_DISPONIBLES = ALGORITMOS_BUSQUEDA


def algoritmos_disponibles() -> tuple[str, ...]:
    """
    Purpose:
        Exponer los algoritmos que la interfaz puede seleccionar.

    Preconditions:
        Ninguna.

    Postconditions:
        Devuelve una tupla inmutable con las etiquetas seleccionables de búsqueda
        (BFS, DFS, UCS, A*, Beam). Minimax y Alfa-Beta siguen disponibles por API,
        pero no se eligen desde la interfaz.

    Complexity:
        O(1).
    """
    return ALGORITMOS_DISPONIBLES


def heuristicas_disponibles() -> tuple[str, ...]:
    """
    Purpose:
        Exponer las heurísticas que la interfaz puede seleccionar para A* y Beam.

    Preconditions:
        Ninguna.

    Postconditions:
        Devuelve una tupla inmutable con 'Manhattan' y 'Exacta'.

    Complexity:
        O(1).

    """
    return HEURISTICAS


def nueva_partida(
    vista: "ScenarioVista",
    algoritmo: str,
    heuristica: str = HEURISTICA_POR_DEFECTO,
) -> Partida:
    """
    Purpose:
        Crear una partida nueva a partir del escenario cargado en la vista.

    Preconditions:
        `vista` proviene de `cargar_escenario`; `algoritmo` está en el catálogo;
        `heuristica` está en el catálogo de heurísticas.

    Postconditions:
        Devuelve una Partida en su estado inicial. Propaga ValueError si el
        algoritmo o la heurística no existen. La heurística solo afecta a A* y
        Beam; los demás algoritmos la conservan pero no la usan.

    Complexity:
        O(F * C + U + T) por la reconstrucción del modelo.
    """
    modelo = cargar_modelo(vista.ruta)
    return Partida(modelo.scenario, modelo.estado, algoritmo, heuristica)


def vista_de_estado(vista: "ScenarioVista", estado: GameState) -> "ScenarioVista":
    """
    Purpose:
        Reflejar el estado actual de la partida en el modelo de vista.

    Preconditions:
        `vista` es la vista base del escenario; `estado` es un GameState del mismo.

    Postconditions:
        Devuelve una copia de la vista con unidades, turno y portador actuales.
        No modifica la vista original.

    Complexity:
        O(U), donde U es el número de unidades.
    """
    unidades = tuple(
        UnidadVista(u.id, u.bando, u.posicion.row, u.posicion.column)
        for u in estado.unidades
    )
    return replace(
        vista,
        unidades=unidades,
        turno=estado.turno,
        portador=estado.portador,
    )


@dataclass(frozen=True)
class UnidadVista:
    """Datos mínimos de una unidad para su representación visual."""

    id: str
    bando: str
    fila: int
    columna: int


@dataclass(frozen=True)
class ScenarioVista:
    """Modelo de vista derivado de un escenario validado."""

    filas: int
    columnas: int
    celdas: tuple[tuple[str, ...], ...]
    terrenos: dict[str, tuple[bool, float | None]]
    bases: dict[str, tuple[int, int]]
    recurso: tuple[int, int]
    unidades: tuple[UnidadVista, ...]
    turno: str
    portador: str | None
    ruta: str


def cargar_escenario(ruta: str) -> ScenarioVista:
    """
    Purpose:
        Leer y validar un escenario JSON y convertirlo en un modelo de vista.

    Preconditions:
        `ruta` apunta a un archivo JSON con el formato del proyecto.

    Postconditions:
        Devuelve un ScenarioVista con tablero, bases, recurso y unidades.
        Lanza ScenarioValidationError, JSONDecodeError u OSError si falla.

    Complexity:
        O(F * C + U + T), F filas, C columnas, U unidades, T tipos de terreno.

    """
    datos = load_scenario(ruta)

    terrenos = {
        nombre: (
            configuracion["transitable"],
            configuracion.get("costo"),
        )
        for nombre, configuracion in datos["tipos_terreno"].items()
    }

    celdas = tuple(tuple(fila) for fila in datos["terreno"])

    # Reutiliza el modelo del dominio para comprobar la coherencia del tablero.
    Board(
        datos["mapa"]["filas"],
        datos["mapa"]["columnas"],
        celdas,
        {
            nombre: Terrain(nombre, transitable, costo)
            for nombre, (transitable, costo) in terrenos.items()
        },
    )

    bases = {
        bando: (posicion["fila"], posicion["columna"])
        for bando, posicion in datos["bases"].items()
    }

    unidades = tuple(
        UnidadVista(
            unidad["id"],
            unidad["bando"],
            unidad["fila"],
            unidad["columna"],
        )
        for unidad in datos["unidades"]
    )

    return ScenarioVista(
        filas=datos["mapa"]["filas"],
        columnas=datos["mapa"]["columnas"],
        celdas=celdas,
        terrenos=terrenos,
        bases=bases,
        recurso=(datos["recurso"]["fila"], datos["recurso"]["columna"]),
        unidades=unidades,
        turno=datos["turno"],
        portador=datos["juego"].get("portador_recurso"),
        ruta=ruta,
    )
