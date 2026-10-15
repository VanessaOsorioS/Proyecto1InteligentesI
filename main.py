import json
from tacticalgrid.io.scenario_loader import load_scenario
from tacticalgrid.io.scenario_validator import ScenarioValidationError


def main():
    try:
        scenario = load_scenario("scenarios/ejemploerror.json")

        print("Escenario cargado correctamente")
        print("Versión:", scenario["version"])
        print("Filas:", scenario["mapa"]["filas"])
        print("Columnas:", scenario["mapa"]["columnas"])
        print("Terrenos:", list(scenario["tipos_terreno"]))

    except ScenarioValidationError as error:
        print("Error de validación:", error)

    except json.JSONDecodeError as error:
        print("El archivo no contiene un JSON válido:", error)

    except OSError as error:
        print("Error al acceder al archivo:", error)


if __name__ == "__main__":
    main()