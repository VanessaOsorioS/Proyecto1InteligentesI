"""Dibujo del tablero de juego con pygame y definición del tema visual."""

from dataclasses import dataclass

import pygame

# --- Tema visual ---
COLOR_FONDO = (26, 28, 33)
COLOR_PANEL = (34, 37, 44)
COLOR_BORDE = (70, 74, 84)
COLOR_BORDE_CELDA = (20, 21, 26)
COLOR_TEXTO = (232, 234, 238)
COLOR_TEXTO_SUAVE = (150, 154, 162)
COLOR_TEXTO_OBSCURO = (38, 40, 46)
COLOR_BOTON = (58, 96, 160)
COLOR_BOTON_HOVER = (80, 122, 196)
COLOR_BOTON_SELECCIONADO = (86, 150, 110)
COLOR_BOTON_DESHABILITADO = (52, 55, 63)
COLOR_TEXTO_DESHABILITADO = (108, 112, 120)
COLOR_RECURSO = (247, 220, 90)
COLOR_PORTADOR = (255, 255, 255)
COLOR_BASE_A = (238, 200, 90)
COLOR_BASE_B = (120, 200, 240)

COLOR_TERRENO = {
    "camino": (176, 168, 140),
    "pasto": (110, 170, 90),
    "bosque": (60, 110, 70),
    "pantano": (96, 112, 84),
    "muro": (70, 70, 78),
    "agua": (80, 130, 180),
}
COLOR_TERRENO_DEFECTO = (140, 140, 150)

COLOR_BANDO = {"A": (210, 84, 72), "B": (74, 124, 214)}

MARGEN = 18
ANCHO_PANEL = 300


@dataclass(frozen=True)
class LayoutTablero:
    """Posición y tamaño de las celdas dentro del área del tablero."""

    x: float
    y: float
    lado: float

    def rect_celda(self, fila: int, columna: int) -> pygame.Rect:
        """Devuelve el rectángulo de la celda (fila, columna)."""
        return pygame.Rect(
            round(self.x + columna * self.lado),
            round(self.y + fila * self.lado),
            round(self.lado),
            round(self.lado),
        )


def calcular_layout(
    ancho_area: int,
    alto_area: int,
    filas: int,
    columnas: int,
) -> LayoutTablero:
    """Centra el tablero en el área disponible con celdas cuadradas."""
    if filas <= 0 or columnas <= 0:
        return LayoutTablero(MARGEN, MARGEN, 1)

    ancho_util = max(ancho_area - 2 * MARGEN, 1)
    alto_util = max(alto_area - 2 * MARGEN, 1)

    lado = min(ancho_util / columnas, alto_util / filas)
    lado = max(lado, 6)

    x = MARGEN + (ancho_util - lado * columnas) / 2
    y = MARGEN + (alto_util - lado * filas) / 2
    return LayoutTablero(x, y, lado)


def dibujar_tablero(pantalla, vista, layout, fuentes, imagen_recurso=None) -> None:
    """
    Purpose:
        Dibujar el tablero, terrenos, bases, recurso y unidades de la vista.

    Preconditions:
        `vista` es un ScenarioVista y `fuentes` un dict de pygame.font.Font.
        `imagen_recurso` es una Surface opcional para el recurso.

    Postconditions:
        El tablero queda dibujado en `pantalla`; no se modifica `vista`.

    Complexity:
        O(F * C + U), F filas, C columnas, U unidades.

    AI usage: Yes
    AI intervention:
        Rutinas de dibujo propuestas con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
    """
    for fila in range(vista.filas):
        for columna in range(vista.columnas):
            rect = layout.rect_celda(fila, columna)
            nombre = vista.celdas[fila][columna]
            transitable, costo = vista.terrenos.get(nombre, (True, None))

            color = COLOR_TERRENO.get(nombre, COLOR_TERRENO_DEFECTO)
            pygame.draw.rect(pantalla, color, rect)

            if not transitable:
                _dibujar_obstaculo(pantalla, rect)
            elif costo is not None:
                _dibujar_costo(pantalla, rect, costo, fuentes["costo"])

            pygame.draw.rect(pantalla, COLOR_BORDE_CELDA, rect, 1)

    _dibujar_bases(pantalla, vista, layout, fuentes["id"])
    _dibujar_recurso(pantalla, vista, layout, imagen_recurso)
    _dibujar_unidades(pantalla, vista, layout, fuentes["id"])


def _dibujar_obstaculo(pantalla, rect) -> None:
    """Marca visualmente una celda no transitable con una cruz."""
    margen = max(3, rect.width // 4)
    pygame.draw.line(
        pantalla,
        COLOR_BORDE_CELDA,
        (rect.left + margen, rect.top + margen),
        (rect.right - margen, rect.bottom - margen),
        2,
    )
    pygame.draw.line(
        pantalla,
        COLOR_BORDE_CELDA,
        (rect.right - margen, rect.top + margen),
        (rect.left + margen, rect.bottom - margen),
        2,
    )


def _dibujar_costo(pantalla, rect, costo, fuente) -> None:
    """Escribe el costo de ingreso en el centro de la celda."""
    texto = fuente.render(_formatear_costo(costo), True, COLOR_TEXTO_OBSCURO)
    pantalla.blit(texto, texto.get_rect(center=rect.center))


def _dibujar_bases(pantalla, vista, layout, fuente) -> None:
    """Dibuja las bases A y B con su color característico."""
    colores = {"A": COLOR_BASE_A, "B": COLOR_BASE_B}
    for bando, (fila, columna) in vista.bases.items():
        rect = layout.rect_celda(fila, columna)
        color = colores.get(bando, COLOR_TEXTO)
        pygame.draw.rect(pantalla, color, rect.inflate(-8, -8), 3, border_radius=5)
        etiqueta = fuente.render(bando, True, color)
        pantalla.blit(etiqueta, (rect.left + 5, rect.top + 3))


def _dibujar_recurso(pantalla, vista, layout, imagen=None) -> None:
    """Dibuja el recurso con la bandera; si no hay imagen, un rombo dorado."""
    rect = layout.rect_celda(vista.recurso[0], vista.recurso[1])

    if imagen is not None:
        lado = max(8, int(rect.width * 0.8))
        escalada = pygame.transform.smoothscale(imagen, (lado, lado))
        pantalla.blit(escalada, escalada.get_rect(center=rect.center))
        return

    centro = rect.center
    radio = max(5, int(rect.width * 0.24))
    puntos = [
        (centro[0], centro[1] - radio),
        (centro[0] + radio, centro[1]),
        (centro[0], centro[1] + radio),
        (centro[0] - radio, centro[1]),
    ]
    pygame.draw.polygon(pantalla, COLOR_RECURSO, puntos)
    pygame.draw.polygon(pantalla, COLOR_BORDE_CELDA, puntos, 2)


def _dibujar_unidades(pantalla, vista, layout, fuente) -> None:
    """Dibuja cada unidad como un disco con su identificador."""
    for unidad in vista.unidades:
        rect = layout.rect_celda(unidad.fila, unidad.columna)
        color = COLOR_BANDO.get(unidad.bando, COLOR_TEXTO)
        radio = max(6, int(min(rect.width, rect.height) * 0.30))

        if unidad.id == vista.portador:
            pygame.draw.circle(pantalla, COLOR_PORTADOR, rect.center, radio + 4, 3)

        pygame.draw.circle(pantalla, color, rect.center, radio)
        pygame.draw.circle(pantalla, COLOR_BORDE_CELDA, rect.center, radio, 2)

        etiqueta = fuente.render(unidad.id, True, COLOR_TEXTO)
        pantalla.blit(etiqueta, etiqueta.get_rect(center=rect.center))


def _formatear_costo(costo) -> str:
    """Muestra enteros sin decimales y el resto con un decimal."""
    if isinstance(costo, float) and costo.is_integer():
        return str(int(costo))
    return str(costo)
