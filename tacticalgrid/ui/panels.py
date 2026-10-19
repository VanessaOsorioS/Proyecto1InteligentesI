"""Panel lateral: botón de carga, HUD con el estado y leyenda de terrenos."""

import os

import pygame

from tacticalgrid.ui.renderer import (
    ANCHO_PANEL,
    COLOR_BORDE,
    COLOR_BOTON,
    COLOR_BOTON_DESHABILITADO,
    COLOR_BOTON_HOVER,
    COLOR_BOTON_SELECCIONADO,
    COLOR_PANEL,
    COLOR_TEXTO,
    COLOR_TEXTO_DESHABILITADO,
    COLOR_TEXTO_SUAVE,
    COLOR_TERRENO,
    COLOR_TERRENO_DEFECTO,
)


class Boton:
    """Zona rectangular clicable con una etiqueta y una clave opcional."""

    def __init__(self, rect: pygame.Rect, texto: str, clave: str | None = None):
        self.rect = rect
        self.texto = texto
        self.clave = clave

    def contiene(self, posicion) -> bool:
        """Indica si un punto de pantalla cae dentro del botón."""
        return self.rect.collidepoint(posicion)


def calcular_panel(ancho_ventana: int, alto_ventana: int) -> pygame.Rect:
    """Devuelve el rectángulo del panel lateral derecho."""
    ancho = ANCHO_PANEL if ancho_ventana >= 900 else max(200, ancho_ventana // 3)
    return pygame.Rect(ancho_ventana - ancho, 0, ancho, alto_ventana)


def construir_boton(rect_panel: pygame.Rect) -> Boton:
    """Crea el botón de carga ajustado al ancho del panel."""
    rect = pygame.Rect(
        rect_panel.x + 16,
        rect_panel.y + 16,
        rect_panel.width - 32,
        44,
    )
    return Boton(rect, "Cargar JSON")


def construir_boton_reiniciar(rect_panel: pygame.Rect, y_inicio: int) -> Boton:
    """Crea el botón de reinicio, debajo del botón de carga y con su mismo ancho."""
    rect = pygame.Rect(rect_panel.x + 16, y_inicio, rect_panel.width - 32, 44)
    return Boton(rect, "Reiniciar")


def construir_botones_algoritmos(
    rect_panel: pygame.Rect,
    y_inicio: int,
    nombres,
    columnas: int = 2,
) -> tuple[Boton, ...]:
    """
    Purpose:
        Crear los botones de selección de algoritmo como una rejilla compacta.

    Preconditions:
        `nombres` es una secuencia de etiquetas; `columnas` >= 1.

    Postconditions:
        Devuelve los Boton en orden fila por fila, cada uno con su clave igual
        a su etiqueta. No dibuja nada ni modifica `rect_panel`.

    Complexity:
        O(N), N cantidad de algoritmos.

    """
    columnas = max(1, columnas)
    espacio = 8
    alto = 28
    ancho_util = rect_panel.width - 32
    ancho = (ancho_util - espacio * (columnas - 1)) // columnas

    botones = []
    for indice, nombre in enumerate(nombres):
        fila, columna = divmod(indice, columnas)
        rect = pygame.Rect(
            rect_panel.x + 16 + columna * (ancho + espacio),
            y_inicio + fila * (alto + espacio),
            ancho,
            alto,
        )
        botones.append(Boton(rect, nombre, nombre))

    return tuple(botones)


def dibujar_algoritmos(pantalla, fuentes, botones, seleccionado, habilitado) -> int:
    """
    Purpose:
        Dibujar los botones de algoritmo resaltando el seleccionado.

    Preconditions:
        `botones` es una secuencia de Boton; `seleccionado` es str o None.

    Postconditions:
        Si `habilitado` es falso los botones se muestran atenuados y no
        responden al puntero. Devuelve la siguiente Y libre bajo la rejilla.

    Complexity:
        O(N), N cantidad de botones.

    """
    if not botones:
        return 0

    encima = pygame.mouse.get_pos()
    fuente = fuentes["pequena"]

    for boton in botones:
        if not habilitado:
            color = COLOR_BOTON_DESHABILITADO
            color_texto = COLOR_TEXTO_DESHABILITADO
        elif boton.clave == seleccionado:
            color = COLOR_BOTON_SELECCIONADO
            color_texto = COLOR_TEXTO
        elif boton.contiene(encima):
            color = COLOR_BOTON_HOVER
            color_texto = COLOR_TEXTO
        else:
            color = COLOR_BOTON
            color_texto = COLOR_TEXTO

        pygame.draw.rect(pantalla, color, boton.rect, border_radius=7)
        etiqueta = fuente.render(boton.texto, True, color_texto)
        pantalla.blit(etiqueta, etiqueta.get_rect(center=boton.rect.center))

    ultima_fila = max(boton.rect.bottom for boton in botones)
    return ultima_fila + 8


def dibujar_panel(
    pantalla,
    vista,
    rect_panel,
    fuentes,
    boton,
    error,
    botones_algoritmos=(),
    algoritmo_seleccionado=None,
    textos_partida=(),
    boton_reiniciar=None,
) -> None:
    """
    Purpose:
        Dibujar el panel lateral con el botón, los algoritmos y el estado.

    Preconditions:
        `rect_panel` delimita el área; `boton` es un Boton; `error` es str o None.
        `botones_algoritmos` son los botones de algoritmo (habilitados si hay vista).
        `textos_partida` son líneas con el estado de la partida (puede estar vacío).

    Postconditions:
        El panel queda dibujado; no se modifica ninguno de los argumentos.

    Complexity:
        O(T + U + N + L), T terrenos, U unidades, N algoritmos, L líneas de partida.

    """
    pygame.draw.rect(pantalla, COLOR_PANEL, rect_panel)
    pygame.draw.line(
        pantalla,
        COLOR_BORDE,
        (rect_panel.left, rect_panel.top),
        (rect_panel.left, rect_panel.bottom),
        2,
    )

    _dibujar_boton(pantalla, boton, fuentes["texto"])
    ultimo = boton
    if boton_reiniciar is not None:
        _dibujar_boton(pantalla, boton_reiniciar, fuentes["texto"])
        ultimo = boton_reiniciar
    y = ultimo.rect.bottom + 12

    if botones_algoritmos:
        y = _dibujar_texto(
            pantalla, "Algoritmo", fuentes["texto"], COLOR_TEXTO, rect_panel, y, 6
        )
        y = dibujar_algoritmos(
            pantalla,
            fuentes,
            botones_algoritmos,
            algoritmo_seleccionado,
            vista is not None,
        )

    if error:
        _dibujar_texto(pantalla, error, fuentes["texto"], COLOR_TEXTO, rect_panel, y)
        return

    if vista is None:
        _dibujar_texto(
            pantalla,
            "Carga un escenario JSON para visualizar el tablero.",
            fuentes["texto"],
            COLOR_TEXTO_SUAVE,
            rect_panel,
            y,
        )
        return

    y = _dibujar_hud(
        pantalla, vista, fuentes, rect_panel, y, algoritmo_seleccionado
    )
    for linea in textos_partida:
        y = _dibujar_texto(pantalla, linea, fuentes["pequena"], COLOR_TEXTO, rect_panel, y, 4)
    _dibujar_leyenda(pantalla, vista, fuentes, rect_panel, y + 10)


def _dibujar_boton(pantalla, boton, fuente) -> None:
    """Dibuja el botón, resaltándolo si el puntero está encima."""
    encima = boton.contiene(pygame.mouse.get_pos())
    color = COLOR_BOTON_HOVER if encima else COLOR_BOTON
    pygame.draw.rect(pantalla, color, boton.rect, border_radius=9)
    etiqueta = fuente.render(boton.texto, True, COLOR_TEXTO)
    pantalla.blit(etiqueta, etiqueta.get_rect(center=boton.rect.center))


def _dibujar_hud(pantalla, vista, fuentes, rect_panel, y, algoritmo=None) -> int:
    """Dibuja los datos generales del escenario y devuelve la siguiente Y."""
    lineas = [
        ("Tablero", f"{vista.filas} x {vista.columnas}"),
        ("Turno", vista.turno),
        ("Portador", vista.portador or "ninguno"),
        ("Unidades", str(len(vista.unidades))),
        ("Algoritmo", algoritmo or "ninguno"),
        ("Archivo", os.path.basename(vista.ruta)),
    ]
    for etiqueta, valor in lineas:
        texto = f"{etiqueta}: {valor}"
        y = _dibujar_texto(pantalla, texto, fuentes["pequena"], COLOR_TEXTO, rect_panel, y, 4)
    return y


def _dibujar_leyenda(pantalla, vista, fuentes, rect_panel, y) -> int:
    """Dibuja la leyenda de terrenos con su color y costo."""
    y = _dibujar_texto(pantalla, "Leyenda", fuentes["texto"], COLOR_TEXTO, rect_panel, y, 8)
    ancho_util = rect_panel.width - 32

    for nombre, (transitable, costo) in vista.terrenos.items():
        if y + 22 > rect_panel.bottom:
            break

        color = COLOR_TERRENO.get(nombre, COLOR_TERRENO_DEFECTO)
        muestra = pygame.Rect(rect_panel.x + 16, y + 2, 18, 18)
        pygame.draw.rect(pantalla, color, muestra, border_radius=4)
        pygame.draw.rect(pantalla, COLOR_BORDE, muestra, 1, border_radius=4)

        if transitable:
            detalle = f"{nombre}  (costo {_costo(costo)})"
        else:
            detalle = f"{nombre}  (bloqueado)"

        etiqueta = fuentes["pequena"].render(detalle, True, COLOR_TEXTO_SUAVE)
        pantalla.blit(etiqueta, (muestra.right + 8, muestra.y))
        y += 24

    return y


def _dibujar_texto(pantalla, texto, fuente, color, rect_panel, y, salto=6) -> int:
    """Dibuja texto con salto de línea y devuelve la siguiente Y."""
    ancho_util = rect_panel.width - 32
    for linea in _envolver(texto, fuente, ancho_util):
        if y + fuente.get_height() > rect_panel.bottom:
            break
        imagen = fuente.render(linea, True, color)
        pantalla.blit(imagen, (rect_panel.x + 16, y))
        y += fuente.get_height() + 2
    return y + salto


def _envolver(texto, fuente, ancho_max) -> list:
    """Divide un texto en líneas que quepan en `ancho_max` píxeles."""
    palabras = str(texto).split()
    lineas = []
    actual = ""

    for palabra in palabras:
        intento = f"{actual} {palabra}".strip()
        if fuente.size(intento)[0] <= ancho_max or not actual:
            actual = intento
        else:
            lineas.append(actual)
            actual = palabra

    if actual:
        lineas.append(actual)
    return lineas


def _costo(costo) -> str:
    """Formatea un costo entero o decimal."""
    if costo is None:
        return "-"
    if isinstance(costo, float) and costo.is_integer():
        return str(int(costo))
    return str(costo)
