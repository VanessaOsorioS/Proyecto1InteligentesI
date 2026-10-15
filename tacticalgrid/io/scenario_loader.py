import json
from pathlib import Path
from tacticalgrid.io.scenario_validator import validate_scenario


def load_scenario(path: str) -> dict:
    """
    Purpose:
        Lee un archivo JSON de escenario.

    Preconditions:
        La ruta debe identificar un archivo accesible.

    Postconditions:
        Devuelve el contenido JSON como diccionario.

    Complexity:
        Tiempo y espacio O(n), donde n es el tamaño del archivo.

    AI usage: Yes
    AI intervention:
        Código de ejemplo propuesto con asistencia de IA.
    Student validation:
        Pendiente de implementación y pruebas por el equipo.
    """

    with Path(path).open("r", encoding="utf-8") as file:
        scenario_data = json.load(file)

    validate_scenario(scenario_data)

    return scenario_data