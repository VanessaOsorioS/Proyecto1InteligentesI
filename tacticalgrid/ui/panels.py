"""Panel lateral: botón de carga, HUD con el estado y leyenda de terrenos."""

import os

import pygame

from tacticalgrid.ui.renderer import (
    ANCHO_PANEL,
    COLOR_BORDE,
    COLOR_BOTON,
    COLOR_BOTON_HOVER,
    COLOR_PANEL,
    COLOR_TEXTO,
    COLOR_TEXTO_SUAVE,
    COLOR_TERRENO,
    COLOR_TERRENO_DEFECTO,
)


class Boton:
    """Zona rectangular clicable con una etiqueta."""

    def __init__(self, rect: pygame.Rect, texto: str):
        self.rect = rect
        self.texto = texto

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


def dibujar_panel(pantalla, vista, rect_panel, fuentes, boton, error) -> None:
    """
    Purpose:
        Dibujar el panel lateral con el botón, el estado y la leyenda.

    Preconditions:
        `rect_panel` delimita el área; `boton` es un Boton; `error` es str o None.

    Postconditions:
        El panel queda dibujado; no se modifica ninguno de los argumentos.

    Complexity:
        O(T + U), T tipos de terreno, U unidades.

    AI usage: Yes
    AI intervention:
        Composición del panel propuesta con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
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
    y = boton.rect.bottom + 18

    if error:
        y = _dibujar_texto(pantalla, error, fuentes["texto"], COLOR_TEXTO, rect_panel, y)
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

    y = _dibujar_hud(pantalla, vista, fuentes, rect_panel, y)
    _dibujar_leyenda(pantalla, vista, fuentes, rect_panel, y + 10)


def _dibujar_boton(pantalla, boton, fuente) -> None:
    """Dibuja el botón, resaltándolo si el puntero está encima."""
    encima = boton.contiene(pygame.mouse.get_pos())
    color = COLOR_BOTON_HOVER if encima else COLOR_BOTON
    pygame.draw.rect(pantalla, color, boton.rect, border_radius=9)
    etiqueta = fuente.render(boton.texto, True, COLOR_TEXTO)
    pantalla.blit(etiqueta, etiqueta.get_rect(center=boton.rect.center))


def _dibujar_hud(pantalla, vista, fuentes, rect_panel, y) -> int:
    """Dibuja los datos generales del escenario y devuelve la siguiente Y."""
    lineas = [
        ("Tablero", f"{vista.filas} x {vista.columnas}"),
        ("Turno", vista.turno),
        ("Portador", vista.portador or "ninguno"),
        ("Unidades", str(len(vista.unidades))),
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
