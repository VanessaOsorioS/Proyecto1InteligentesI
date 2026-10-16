"""Carga de escenarios JSON y puente hacia los objetos del dominio.

`load_scenario` mantiene su contrato histórico (devuelve el `dict` validado)
para no romper la interfaz existente. `construir_modelo` y `cargar_modelo`
añaden la conversión de ese `dict` a las entidades del dominio: `Board`,
`Scenario` y `GameState`.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from tacticalgrid.domain.board import Board
from tacticalgrid.domain.position import Position
from tacticalgrid.domain.scenario import Scenario
from tacticalgrid.domain.state import GameState
from tacticalgrid.domain.terrain import Terrain
from tacticalgrid.domain.unit import Unit
from tacticalgrid.io.scenario_validator import validate_scenario


@dataclass(frozen=True)
class ModeloEscenario:
    """Modelo de dominio completo: configuración estática y estado actual.

    Attributes:
        scenario: Configuración estática (tablero, bases, recurso, prueba).
        estado: Estado dinámico e inmutable (unidades, turno, portador, contadores).
    """

    scenario: Scenario
    estado: GameState


def load_scenario(path: str) -> dict:

    with Path(path).open("r", encoding="utf-8") as file:
        scenario_data = json.load(file)

    validate_scenario(scenario_data)

    return scenario_data


def construir_modelo(datos: dict) -> ModeloEscenario:
    """
    Purpose:
        Convertir un escenario JSON ya validado en entidades del dominio.

    Preconditions:
        `datos` es el diccionario validado por `validate_scenario`.

    Postconditions:
        Devuelve un ModeloEscenario con Board, Scenario y GameState completos.
        Representa cualquier cantidad de unidades sin fijar un número.

    Complexity:
        O(F * C + U + T), F filas, C columnas, U unidades, T tipos de terreno.

    """
    terrenos = {
        nombre: Terrain(nombre, configuracion["transitable"], configuracion.get("costo"))
        for nombre, configuracion in datos["tipos_terreno"].items()
    }

    celdas = tuple(tuple(fila) for fila in datos["terreno"])

    tablero = Board(
        datos["mapa"]["filas"],
        datos["mapa"]["columnas"],
        celdas,
        terrenos,
    )

    bases = {
        bando: Position(posicion["fila"], posicion["columna"])
        for bando, posicion in datos["bases"].items()
    }

    recurso = Position(datos["recurso"]["fila"], datos["recurso"]["columna"])

    unidades = tuple(
        Unit(
            unidad["id"],
            unidad["bando"],
            unidad["tipo"],
            Position(unidad["fila"], unidad["columna"]),
        )
        for unidad in datos["unidades"]
    )

    juego = datos["juego"]

    scenario = Scenario(
        version=datos["version"],
        tablero=tablero,
        bases=bases,
        recurso=recurso,
        profundidad_maxima_minimax=juego.get("profundidad_maxima_minimax"),
        prueba=datos.get("prueba"),
    )

    estado = GameState(
        unidades=unidades,
        turno=datos["turno"],
        portador=juego["portador_recurso"],
        posicion_recurso=recurso,
    )

    return ModeloEscenario(scenario=scenario, estado=estado)


def cargar_modelo(path: str) -> ModeloEscenario:
    """
    Purpose:
        Cargar un escenario externo y devolver su modelo de dominio completo.

    Preconditions:
        `path` apunta a un archivo JSON con el formato del proyecto.

    Postconditions:
        Devuelve un ModeloEscenario inmutable y sin perder información del
        archivo. Propaga ScenarioValidationError, JSONDecodeError u OSError.

    Complexity:
        O(F * C + U + T), la del cargador más la construcción del modelo.

    """
    return construir_modelo(load_scenario(path))
