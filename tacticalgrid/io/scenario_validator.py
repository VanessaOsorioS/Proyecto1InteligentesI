from typing import Any


class ScenarioValidationError(ValueError):
    """Error cuando un escenario no cumple las reglas del proyecto."""


def validate_scenario(data: dict[str, Any]) -> None:
    """
    Purpose:
        Verifica que un escenario cumpla las reglas del formato JSON.

    Preconditions:
        Recibe los datos obtenidos de un archivo JSON.

    Postconditions:
        Si es válido, termina sin errores.
        Si es inválido, lanza ScenarioValidationError.

    Complexity:
        O(F * C + U + T), donde:
        F = filas, C = columnas,
        U = unidades, T = tipos de terreno.

    AI usage: Yes
    AI intervention:
        Implementación inicial propuesta con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
    """
    if not isinstance(data, dict):
        raise ScenarioValidationError(
            "El escenario debe ser un objeto JSON."
        )

    validate_required_fields(data)
    validate_map(data)
    validate_terrain_types(data)
    validate_positions(data)
    validate_units(data)
    validate_game(data)


def validate_required_fields(data: dict) -> None:
    """Comprueba la presencia de los campos principales."""

    required = [
        "version",
        "mapa",
        "tipos_terreno",
        "terreno",
        "bases",
        "recurso",
        "unidades",
        "turno",
        "juego",
    ]

    for field in required:
        if field not in data:
            raise ScenarioValidationError(
                f"Falta el campo obligatorio: '{field}'."
            )

    if data["version"] != "1.0":
        raise ScenarioValidationError(
            "Versión de escenario no compatible."
        )

    if not isinstance(data["mapa"], dict):
        raise ScenarioValidationError("'mapa' debe ser un objeto.")

    if not isinstance(data["bases"], dict):
        raise ScenarioValidationError("'bases' debe ser un objeto.")

    if not isinstance(data["juego"], dict):
        raise ScenarioValidationError("'juego' debe ser un objeto.")

    if not isinstance(data["turno"], str) or data["turno"] not in ("A", "B"):
        raise ScenarioValidationError(
            "'turno' debe ser 'A' o 'B'."
        )

    if "portador_recurso" not in data["juego"]:
        raise ScenarioValidationError(
            "Falta 'juego.portador_recurso'."
        )

    if "A" not in data["bases"] or "B" not in data["bases"]:
        raise ScenarioValidationError(
            "Deben existir las bases A y B."
        )

    # 'prueba' es opcional según la descripción del documento.
    if "prueba" in data and not isinstance(data["prueba"], dict):
        raise ScenarioValidationError(
            "'prueba' debe ser un objeto."
        )


def validate_map(data: dict) -> None:
    """Comprueba dimensiones y consistencia de la matriz."""

    mapa = data["mapa"]
    filas = mapa.get("filas")
    columnas = mapa.get("columnas")

    if type(filas) is not int or filas <= 0:
        raise ScenarioValidationError(
            "'mapa.filas' debe ser un entero positivo."
        )

    if type(columnas) is not int or columnas <= 0:
        raise ScenarioValidationError(
            "'mapa.columnas' debe ser un entero positivo."
        )

    terreno = data["terreno"]

    if not isinstance(terreno, list) or len(terreno) != filas:
        raise ScenarioValidationError(
            "La matriz de terreno no coincide con el número de filas."
        )

    for i, fila in enumerate(terreno):
        if not isinstance(fila, list) or len(fila) != columnas:
            raise ScenarioValidationError(
                f"La fila {i} no tiene {columnas} columnas."
            )


def validate_terrain_types(data: dict) -> None:
    """Comprueba el catálogo de terrenos y las celdas."""

    catalogo = data["tipos_terreno"]

    if not isinstance(catalogo, dict) or not catalogo:
        raise ScenarioValidationError(
            "'tipos_terreno' debe ser un catálogo no vacío."
        )

    for nombre, configuracion in catalogo.items():
        if not isinstance(configuracion, dict):
            raise ScenarioValidationError(
                f"Configuración inválida del terreno '{nombre}'."
            )

        transitable = configuracion.get("transitable")

        if not isinstance(transitable, bool):
            raise ScenarioValidationError(
                f"El terreno '{nombre}' necesita un valor booleano "
                "en 'transitable'."
            )

        if transitable:
            costo = configuracion.get("costo")

            if (
                type(costo) not in (int, float)
                or costo <= 0
            ):
                raise ScenarioValidationError(
                    f"El terreno '{nombre}' debe tener "
                    "un costo numérico positivo."
                )

    for fila, celdas in enumerate(data["terreno"]):
        for columna, tipo in enumerate(celdas):
            if tipo not in catalogo:
                raise ScenarioValidationError(
                    f"Terreno desconocido '{tipo}' "
                    f"en ({fila}, {columna})."
                )


def validate_position(position: Any, data: dict, label: str) -> None:
    """Comprueba que una posición pertenezca a una celda transitable."""

    if not isinstance(position, dict):
        raise ScenarioValidationError(
            f"La posición de '{label}' debe ser un objeto."
        )

    fila = position.get("fila")
    columna = position.get("columna")

    if type(fila) is not int or type(columna) is not int:
        raise ScenarioValidationError(
            f"Las coordenadas de '{label}' deben ser enteros."
        )

    filas = data["mapa"]["filas"]
    columnas = data["mapa"]["columnas"]

    if not (0 <= fila < filas and 0 <= columna < columnas):
        raise ScenarioValidationError(
            f"'{label}' está fuera del mapa: ({fila}, {columna})."
        )

    tipo = data["terreno"][fila][columna]

    if not data["tipos_terreno"][tipo]["transitable"]:
        raise ScenarioValidationError(
            f"'{label}' se encuentra sobre un obstáculo "
            f"en ({fila}, {columna})."
        )


def validate_positions(data: dict) -> None:
    """Comprueba las posiciones de bases y recurso."""

    validate_position(data["bases"]["A"], data, "Base A")
    validate_position(data["bases"]["B"], data, "Base B")
    validate_position(data["recurso"], data, "Recurso")


def validate_units(data: dict) -> None:
    """
    Purpose:
        Comprobar identificadores, bandos y posiciones de las unidades.

    Preconditions:
        `data` contiene las claves `bases` y `unidades` ya validadas.

    Postconditions:
        No devuelve nada si todo es válido. Se permite compartir celda solo
        en la base propia y entre unidades del mismo bando. Lanza
        ScenarioValidationError en caso contrario.

    Complexity:
        O(U), donde U es el número de unidades.

    AI usage: No
    AI intervention:
        Ninguna.
    Student validation:
        Pendiente de revisión por el equipo.
    """

    unidades = data["unidades"]

    if not isinstance(unidades, list):
        raise ScenarioValidationError(
            "'unidades' debe ser una lista."
        )

    bases = {
        bando: (
            data["bases"][bando]["fila"],
            data["bases"][bando]["columna"],
        )
        for bando in ("A", "B")
    }
    identificadores = set()
    cantidad = {"A": 0, "B": 0}
    posiciones: dict[tuple[int, int], str] = {}

    for indice, unidad in enumerate(unidades):
        if not isinstance(unidad, dict):
            raise ScenarioValidationError(
                f"La unidad {indice} debe ser un objeto."
            )

        identificador = unidad.get("id")
        bando = unidad.get("bando")
        tipo = unidad.get("tipo")

        if not isinstance(identificador, str) or not identificador:
            raise ScenarioValidationError(
                f"La unidad {indice} necesita un identificador."
            )

        if identificador in identificadores:
            raise ScenarioValidationError(
                f"Identificador duplicado: '{identificador}'."
            )

        identificadores.add(identificador)

        if bando not in ("A", "B"):
            raise ScenarioValidationError(
                f"La unidad '{identificador}' tiene un bando inválido."
            )

        cantidad[bando] += 1

        if not isinstance(tipo, str) or not tipo:
            raise ScenarioValidationError(
                f"La unidad '{identificador}' necesita un tipo."
            )

        validate_position(
            {"fila": unidad.get("fila"), "columna": unidad.get("columna")},
            data,
            f"Unidad {identificador}",
        )

        clave = (unidad.get("fila"), unidad.get("columna"))
        bando_previo = posiciones.get(clave)
        if bando_previo is not None:
            if bando_previo != bando or bases[bando] != clave:
                raise ScenarioValidationError(
                    "Dos unidades solo pueden compartir la base propia "
                    f"del mismo bando; posicion duplicada: {clave}."
                )
        else:
            posiciones[clave] = bando

    # El ejemplo 4x4 del documento tiene dos unidades por bando.
    # Para los escenarios completos de desarrollo se deben usar
    # al menos tres por equipo. Esa regla puede validarse aparte.


def validate_game(data: dict) -> None:
    """Comprueba la posesión del recurso y la profundidad."""

    juego = data["juego"]
    portador = juego["portador_recurso"]

    identificadores = {
        unidad["id"] for unidad in data["unidades"]
    }

    if portador is not None and portador not in identificadores:
        raise ScenarioValidationError(
            f"El portador '{portador}' no corresponde "
            "a ninguna unidad existente."
        )

    if "profundidad_maxima_minimax" in juego:
        profundidad = juego["profundidad_maxima_minimax"]

        if type(profundidad) is not int or profundidad < 1:
            raise ScenarioValidationError(
                "'profundidad_maxima_minimax' debe "
                "ser un entero positivo."
            )
