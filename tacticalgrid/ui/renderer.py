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

_CACHE_ESCALADOS: dict[tuple[int, int, int], tuple[pygame.Surface, pygame.Surface]] = {}
"""Caché de superficies reescaladas: (id de origen, ancho, alto) -> (origen, escalada)."""

_CACHE_FUENTES: dict[int, pygame.font.Font] = {}
"""Caché de fuentes para el identificador: tamaño en píxeles -> fuente."""


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

    def centro(self, fila: float, columna: float) -> tuple[float, float]:
        """Centro en píxeles de una posición, admitiendo valores fraccionarios."""
        return (
            self.x + (columna + 0.5) * self.lado,
            self.y + (fila + 0.5) * self.lado,
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


def dibujar_tablero(
    pantalla,
    vista,
    layout,
    fuentes,
    imagen_recurso=None,
    previas=None,
    progreso=1.0,
    recogida=False,
    imagenes_terreno=None,
    imagenes_bando=None,
) -> None:
    """
    Purpose:
        Dibujar el tablero, terrenos, bases, recurso y unidades de la vista.

    Preconditions:
        `vista` es un ScenarioVista y `fuentes` un dict de pygame.font.Font.
        `imagen_recurso` es una Surface opcional para el recurso. `previas` es
        un dict id -> (fila, columna) de la posición anterior y `progreso` en
        [0, 1] indica cuánto se ha desplazado cada ficha hacia la actual.
        `imagenes_terreno` e `imagenes_bando` son dicts opcionales que asocian
        el nombre del terreno o el bando con una Surface ya recortada.

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

            imagen_terreno = _imagen_de_mapa(imagenes_terreno, nombre)
            if imagen_terreno is not None:
                escalada = _escalar_imagen(
                    imagen_terreno,
                    rect.width,
                    rect.height,
                    conservar_proporcion=False,
                )
                pantalla.blit(escalada, rect.topleft)

            if not transitable:
                _dibujar_obstaculo(pantalla, rect)
            elif costo is not None:
                _dibujar_costo(
                    pantalla,
                    rect,
                    costo,
                    fuentes["costo"],
                    con_fondo=imagen_terreno is not None,
                )

            pygame.draw.rect(pantalla, COLOR_BORDE_CELDA, rect, 1)

    # Durante el paso en que la unidad recoge el recurso, la bandera grande
    # sigue en su casilla de origen y la pequeña aparece solo al terminar.
    en_recogida = recogida and progreso < 1.0

    _dibujar_bases(pantalla, vista, layout, fuentes["id"])
    _dibujar_recurso(pantalla, vista, layout, imagen_recurso, en_recogida)
    _dibujar_unidades(
        pantalla,
        vista,
        layout,
        fuentes["id"],
        previas,
        progreso,
        imagen_recurso,
        ocultar_bandera=en_recogida,
        imagenes_bando=imagenes_bando,
    )


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


def _dibujar_costo(pantalla, rect, costo, fuente, con_fondo=False) -> None:
    """
    Purpose:
        Escribir el costo de ingreso en el centro de la celda.

    Preconditions:
        `rect` es el rectángulo de la celda y `fuente` una pygame.font.Font.
        `con_fondo` pide un disco oscuro detrás del número para que se lea
        sobre una imagen de terreno.

    Postconditions:
        El número queda dibujado en `pantalla`; no se modifica `rect`.

    Complexity:
        O(1) más el coste de dibujar el texto.

    AI usage: Yes
    AI intervention:
        Ajuste de contraste sobre imágenes propuesto con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
    """
    if con_fondo:
        fondo = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.circle(
            fondo,
            (20, 22, 26, 170),
            (rect.width // 2, rect.height // 2),
            max(7, int(rect.width * 0.24)),
        )
        pantalla.blit(fondo, rect.topleft)

    color = COLOR_TEXTO if con_fondo else COLOR_TEXTO_OBSCURO
    texto = fuente.render(_formatear_costo(costo), True, color)
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


def _dibujar_recurso(pantalla, vista, layout, imagen=None, en_recogida=False) -> None:
    """Dibuja el recurso en su celda de origen mientras nadie lo transporta.

    Cuando una unidad lo lleva, la bandera se dibuja sobre esa unidad en
    `_dibujar_unidades`. Durante el paso de recogida (`en_recogida`) la bandera
    grande se mantiene en su origen hasta que la unidad llega.
    """
    if vista.portador is not None and not en_recogida:
        return

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


def _dibujar_bandera_pequena(pantalla, centro, radio, imagen=None) -> None:
    """Dibuja una bandera pequeña en la esquina superior derecha del disco portador."""
    lado = max(8, int(radio * 1.1))
    cx = round(centro[0] + radio * 0.75)
    cy = round(centro[1] - radio * 0.75)

    if imagen is not None:
        escalada = pygame.transform.smoothscale(imagen, (lado, lado))
        pantalla.blit(escalada, escalada.get_rect(center=(cx, cy)))
        return

    mitad = lado // 2
    puntos = [(cx, cy - mitad), (cx + mitad, cy), (cx, cy + mitad), (cx - mitad, cy)]
    pygame.draw.polygon(pantalla, COLOR_RECURSO, puntos)
    pygame.draw.polygon(pantalla, COLOR_BORDE_CELDA, puntos, 1)


def _dibujar_bandera_portador(pantalla, centro, lado, imagen=None) -> None:
    """
    Purpose:
        Dibujar la bandera del portador centrada en un punto, con tamaño fijo.

    Preconditions:
        `centro` es una tupla (x, y) en píxeles; `lado` es el tamaño deseado.
        `imagen` es una Surface opcional para la bandera.

    Postconditions:
        La bandera queda dibujada en `pantalla`.

    Complexity:
        O(1) más el coste de dibujar la imagen.

    AI usage: Yes
    AI intervention:
        Rutina de dibujo propuesta con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
    """
    lado = max(8, int(lado))

    if imagen is not None:
        escalada = _escalar_imagen(imagen, lado, lado)
        pantalla.blit(escalada, escalada.get_rect(center=centro))
        return

    cx, cy = centro
    mitad = lado // 2
    puntos = [(cx, cy - mitad), (cx + mitad, cy), (cx, cy + mitad), (cx - mitad, cy)]
    pygame.draw.polygon(pantalla, COLOR_RECURSO, puntos)
    pygame.draw.polygon(pantalla, COLOR_BORDE_CELDA, puntos, 1)


def _desplazamientos_apilados(cantidad: int, lado: float) -> list[tuple[float, float]]:
    """
    Purpose:
        Calcular desplazamientos pequeños para unidades que comparten celda.

    Preconditions:
        `cantidad` es el número de unidades en la celda y `lado` es el tamaño
        de la celda en píxeles.

    Postconditions:
        Devuelve una lista de desplazamientos (dx, dy) en píxeles, uno por
        unidad, distribuidos en una rejilla dentro de la celda.

    Complexity:
        O(cantidad).

    AI usage: No
    AI intervention:
        Ninguna.
    Student validation:
        Pendiente de revisión por el equipo.
    """
    if cantidad <= 1:
        return [(0.0, 0.0)]

    columnas = 2
    filas = (cantidad + columnas - 1) // columnas
    paso = min(lado * 0.28, lado * 0.62 / max(columnas, filas))
    desplazamientos = []
    for indice in range(cantidad):
        fila = indice // columnas
        columna = indice % columnas
        dx = (columna - (columnas - 1) / 2) * paso
        dy = (fila - (filas - 1) / 2) * paso
        desplazamientos.append((dx, dy))
    return desplazamientos


def _dibujar_unidades(
    pantalla,
    vista,
    layout,
    fuente,
    previas=None,
    progreso=1.0,
    imagen=None,
    ocultar_bandera=False,
    imagenes_bando=None,
) -> None:
    """
    Purpose:
        Dibujar cada unidad con su identificador, interpolando el movimiento.

    Preconditions:
        `vista` es un ScenarioVista. `previas` es un dict id -> (fila, columna)
        y `progreso` está en [0, 1]. `imagen` es la bandera del recurso y
        `imagenes_bando` asocia cada bando con un sprite ya recortado.

    Postconditions:
        Cada unidad se dibuja con su sprite si el bando tiene imagen o con un
        disco de color en caso contrario. Si varias unidades comparten celda,
        se desplazan ligeramente para que todas sean visibles. La unidad
        portadora lleva además una bandera pequeña que se mueve con ella y se
        dibuja al final.

    Complexity:
        O(U), U unidades.

    AI usage: Yes
    AI intervention:
        Sustitución de discos por sprites propuesta con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
    """
    radio = max(6, int(layout.lado * 0.30))
    animar = bool(previas) and progreso < 1.0
    imagenes_bando = imagenes_bando or {}

    ids_por_celda: dict[tuple[int, int], list[str]] = {}
    for unidad in vista.unidades:
        ids_por_celda.setdefault((unidad.fila, unidad.columna), []).append(
            unidad.id
        )

    desplazamientos: dict[str, tuple[float, float]] = {}
    for ids in ids_por_celda.values():
        for id_unidad, desplazamiento in zip(
            sorted(ids), _desplazamientos_apilados(len(ids), layout.lado)
        ):
            desplazamientos[id_unidad] = desplazamiento

    for unidad in sorted(
        vista.unidades, key=lambda u: (u.id == vista.portador, u.id)
    ):
        fila, columna = float(unidad.fila), float(unidad.columna)
        if animar and unidad.id in previas:
            fila_previa, columna_previa = previas[unidad.id]
            fila = fila_previa + (fila - fila_previa) * progreso
            columna = columna_previa + (columna - columna_previa) * progreso

        centro_x, centro_y = layout.centro(fila, columna)
        dx, dy = desplazamientos.get(unidad.id, (0.0, 0.0))
        centro = (round(centro_x + dx), round(centro_y + dy))
        color = COLOR_BANDO.get(unidad.bando, COLOR_TEXTO)
        sprite = imagenes_bando.get(unidad.bando)

        if sprite is None:
            if unidad.id == vista.portador:
                pygame.draw.circle(pantalla, COLOR_PORTADOR, centro, radio + 4, 3)

            pygame.draw.circle(pantalla, color, centro, radio)
            pygame.draw.circle(pantalla, COLOR_BORDE_CELDA, centro, radio, 2)

            etiqueta = fuente.render(unidad.id, True, COLOR_TEXTO)
            pantalla.blit(etiqueta, etiqueta.get_rect(center=centro))

            if unidad.id == vista.portador and not ocultar_bandera:
                _dibujar_bandera_pequena(pantalla, centro, radio, imagen)
            continue

        lado_sprite = layout.lado * 0.92
        escalado = _escalar_imagen(sprite, lado_sprite, lado_sprite)
        base_y = round(centro[1] + layout.lado * 0.44)
        destino = escalado.get_rect(midbottom=(centro[0], base_y))

        if unidad.id == vista.portador:
            halo = pygame.Rect(
                0,
                0,
                max(10, int(layout.lado * 0.78)),
                max(6, int(layout.lado * 0.22)),
            )
            halo.center = (centro[0], round(base_y - layout.lado * 0.06))
            pygame.draw.ellipse(
                pantalla,
                COLOR_PORTADOR,
                halo,
                max(2, int(layout.lado * 0.02)),
            )

        pantalla.blit(escalado, destino)

        fuente_id = _fuente_id(layout.lado)
        etiqueta = fuente_id.render(unidad.id, True, COLOR_TEXTO)
        sombra = fuente_id.render(unidad.id, True, COLOR_BORDE_CELDA)
        desfase = max(1, int(layout.lado * 0.012))
        centro_etiqueta = (
            destino.centerx,
            destino.centery + int(layout.lado * 0.14),
        )
        pantalla.blit(
            sombra,
            sombra.get_rect(
                center=(centro_etiqueta[0] + desfase, centro_etiqueta[1] + desfase)
            ),
        )
        pantalla.blit(etiqueta, etiqueta.get_rect(center=centro_etiqueta))

        if unidad.id == vista.portador and not ocultar_bandera:
            _dibujar_bandera_portador(
                pantalla,
                (
                    destino.right + round(layout.lado * 0.05),
                    destino.top + round(layout.lado * 0.20),
                ),
                max(8, int(layout.lado * 0.30)),
                imagen,
            )


def _fuente_id(lado):
    """
    Purpose:
        Obtener una fuente para el identificador proporcional a la celda.

    Preconditions:
        `lado` es el tamaño de la celda en píxeles.

    Postconditions:
        Devuelve una pygame.font.Font en negrita; reutiliza las ya creadas.

    Complexity:
        O(1) esperado tras la primera llamada por tamaño.

    AI usage: Yes
    AI intervention:
        Escalado del identificador propuesto con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
    """
    tamano = max(11, int(lado * 0.13))
    fuente = _CACHE_FUENTES.get(tamano)
    if fuente is None:
        if len(_CACHE_FUENTES) > 24:
            _CACHE_FUENTES.clear()
        fuente = pygame.font.SysFont("consolas", tamano, bold=True)
        _CACHE_FUENTES[tamano] = fuente
    return fuente


def _imagen_de_mapa(imagenes, nombre):
    """
    Purpose:
        Buscar la imagen asociada a un nombre de terreno sin distinguir mayúsculas.

    Preconditions:
        `imagenes` es un dict nombre -> Surface o None; `nombre` es el nombre
        del terreno tal como aparece en el escenario.

    Postconditions:
        Devuelve la Surface correspondiente o None si no existe.

    Complexity:
        O(1) esperado.

    AI usage: Yes
    AI intervention:
        Normalización del nombre propuesta con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
    """
    if not imagenes:
        return None
    return imagenes.get(str(nombre).strip().lower())


def _escalar_imagen(imagen, ancho, alto, conservar_proporcion=True):
    """
    Purpose:
        Escalar una imagen y reutilizar el resultado si ya se calculó.

    Preconditions:
        `imagen` es una Surface; `ancho` y `alto` son positivos. Si
        `conservar_proporcion` es verdadero, la imagen cabe dentro de la caja.

    Postconditions:
        Devuelve una Surface escalada; no modifica `imagen`.

    Complexity:
        O(1) en aciertos de caché y O(A * B) al escalar, A y B destino.

    AI usage: Yes
    AI intervention:
        Caché por tamaño propuesta con asistencia de IA.
    Student validation:
        Pendiente de pruebas y revisión por el equipo.
    """
    ancho = max(1, int(ancho))
    alto = max(1, int(alto))

    if conservar_proporcion:
        proporcion = imagen.get_width() / max(1, imagen.get_height())
        if ancho / alto > proporcion:
            ancho = max(1, round(alto * proporcion))
        else:
            alto = max(1, round(ancho / proporcion))

    clave = (id(imagen), ancho, alto)
    entrada = _CACHE_ESCALADOS.get(clave)
    if entrada is not None and entrada[0] is imagen:
        return entrada[1]

    if len(_CACHE_ESCALADOS) > 128:
        _CACHE_ESCALADOS.clear()

    escalada = pygame.transform.smoothscale(imagen, (ancho, alto))
    _CACHE_ESCALADOS[clave] = (imagen, escalada)
    return escalada


def _formatear_costo(costo) -> str:
    """Muestra enteros sin decimales y el resto con un decimal."""
    if isinstance(costo, float) and costo.is_integer():
        return str(int(costo))
    return str(costo)
