import json
from pathlib import Path
from tacticalgrid.io.scenario_validator import validate_scenario


def load_scenario(path: str) -> dict:

    with Path(path).open("r", encoding="utf-8") as file:
        scenario_data = json.load(file)

    validate_scenario(scenario_data)

    return scenario_data