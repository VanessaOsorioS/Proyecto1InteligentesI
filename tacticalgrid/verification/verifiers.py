"""Comprobación de los caminos devueltos por los algoritmos de búsqueda."""

from tacticalgrid.search.problem import Problema, ResultadoBusqueda

TOLERANCIA_COSTO = 1e-9


def verificar_camino(problema: Problema, resultado: ResultadoBusqueda) -> None:
    """
    Purpose:
        Comprobar que un camino es válido para el problema: parte del inicio,
        termina en una meta, cada paso es un sucesor real y el costo coincide.

    Preconditions:
        `problema` cumple la interfaz Problema; `resultado` proviene de una
        búsqueda sobre ese mismo problema.

    Postconditions:
        No devuelve nada si el camino es válido o si no hubo éxito. Lanza
        ValueError si alguna comprobación falla.

    Complexity:
        O(L), donde L es la longitud del camino (con a lo sumo cuatro sucesores
        por nodo).

    AI usage: Yes
    AI intervention:
        Verificador propuesto con asistencia de IA.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    if not resultado.exito:
        return

    camino = resultado.camino
    if not camino or camino[0] != problema.inicio:
        raise ValueError("El camino no parte de la posición inicial.")

    if not problema.es_objetivo(camino[-1]):
        raise ValueError("El camino no termina en una meta.")

    costo = 0.0
    for origen, destino in zip(camino, camino[1:]):
        sucesores = dict(problema.sucesores(origen))
        if destino not in sucesores:
            raise ValueError(f"Paso no válido de {origen} a {destino}.")
        costo += sucesores[destino]

    if abs(costo - resultado.costo) > TOLERANCIA_COSTO:
        raise ValueError(
            f"El costo declarado ({resultado.costo}) no coincide con el real ({costo})."
        )
