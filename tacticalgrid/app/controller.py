"""Orquestación entre la capa de E/S y la interfaz gráfica.

Transforma el diccionario validado que devuelve `load_scenario` en un modelo de
vista listo para dibujar, reutilizando la clase `Board` del dominio para validar
la coherencia del tablero.
"""

from dataclasses import dataclass

from tacticalgrid.domain.board import Board
from tacticalgrid.domain.terrain import Terrain
from tacticalgrid.io.scenario_loader import load_scenario

ALGORITMOS_DISPONIBLES = (
    "BFS",
    "DFS",
    "UCS",
    "A*",
    "Beam k=1",
    "Beam k=2",
    "Beam k=4",
    "Beam k=8",
)


def algoritmos_disponibles() -> tuple[str, ...]:
    """
    Purpose:
        Exponer los algoritmos de búsqueda que la interfaz puede ofrecer.

    Preconditions:
        Ninguna.

    Postconditions:
        Devuelve una tupla inmutable con las etiquetas seleccionables.
        Es la única fuente del catálogo; la UI no conoce `search/`.

    Complexity:
        O(1).

    """
    return ALGORITMOS_DISPONIBLES


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

    AI usage: Yes
    AI intervention:
        Adaptador dict -> vista propuesto con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
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
