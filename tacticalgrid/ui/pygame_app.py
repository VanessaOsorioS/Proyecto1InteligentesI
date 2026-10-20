"""Aplicación pygame: ventana, bucle principal, carga de escenarios y partida animada."""

import json
import os

import pygame
import tkinter
from tkinter import filedialog

from tacticalgrid.app.controller import (
    cargar_escenario,
    algoritmos_disponibles,
    nueva_partida,
    vista_de_estado,
    ScenarioVista,
)
from tacticalgrid.io.scenario_validator import ScenarioValidationError
from tacticalgrid.ui import panels, renderer

INTERVALO_PASO_MS = 600
"""Tiempo entre turnos; también es la duración de la animación de cada ficha."""


class PygameApp:
    """Ventana de visualización del tablero con carga de JSON y partida automática."""

    def __init__(self, ruta_inicial: str | None = None, tamano=(1100, 720)):
        pygame.init()
        pygame.display.set_caption("TacticalGrid")
        self.pantalla = pygame.display.set_mode(tamano, pygame.RESIZABLE)
        self.reloj = pygame.time.Clock()

        self.imagen_recurso = self._cargar_imagen("bandera_recurso.png")
        self.imagenes_terreno = {}
        self.imagenes_bando = {}

        imagen_pantano = self._cargar_imagen("Pantano.png")
        if imagen_pantano is not None:
            self.imagenes_terreno["pantano"] = imagen_pantano

        for bando, archivo in (("A", "PeonRojo.png"), ("B", "PeonVerde.png")):
            imagen_peon = self._cargar_imagen(archivo, recortar=True)
            if imagen_peon is not None:
                self.imagenes_bando[bando] = imagen_peon

        self.fuentes = {
            "titulo": pygame.font.SysFont("consolas", 22, bold=True),
            "texto": pygame.font.SysFont("consolas", 16),
            "pequena": pygame.font.SysFont("consolas", 13),
            "costo": pygame.font.SysFont("consolas", 12, bold=True),
            "id": pygame.font.SysFont("consolas", 12, bold=True),
        }

        self.vista: ScenarioVista | None = None
        self.error: str | None = None
        self.boton = None
        self.boton_reiniciar = None
        self.algoritmos = algoritmos_disponibles()
        self.botones_algoritmos = ()
        self.algoritmo_seleccionado: str | None = None
        self.partida = None
        self.ultimo_paso_ms: int | None = None

        if ruta_inicial and os.path.exists(ruta_inicial):
            self.cargar(ruta_inicial)

    def _cargar_imagen(self, archivo: str, recortar: bool = False):
        """
        Purpose:
            Cargar una imagen de `ui/assets` con canal alfa.

        Preconditions:
            `archivo` es el nombre del archivo dentro de `ui/assets`; la
            pantalla de pygame ya está inicializada.

        Postconditions:
            Devuelve la Surface cargada o None si el archivo no existe o no es
            una imagen válida. Si `recortar`, elimina el margen transparente.

        Complexity:
            O(P), P píxeles de la imagen.

        AI usage: Yes
        AI intervention:
            Carga tolerante a errores y recorte propuestos con asistencia de IA.
        Student validation:
            Pendiente de pruebas y revisión por el equipo.
        """
        ruta = os.path.join(os.path.dirname(__file__), "assets", archivo)
        try:
            imagen = pygame.image.load(ruta).convert_alpha()
        except (pygame.error, FileNotFoundError):
            return None

        if recortar:
            contenido = imagen.get_bounding_rect()
            if contenido.width > 0 and contenido.height > 0:
                imagen = imagen.subsurface(contenido).copy()
        return imagen

    def cargar(self, ruta: str) -> None:
        """
        Purpose:
            Cargar un escenario, descartando cualquier partida anterior.

        Preconditions:
            `ruta` es una ruta de archivo JSON.

        Postconditions:
            Actualiza `self.vista` o `self.error`; `self.partida` queda en None.

        Complexity:
            O(F * C + U), la del cargador del escenario.

        AI usage: Yes
        AI intervention:
            Manejo de errores propuesto con asistencia de IA.
        Student validation:
            Pendiente de pruebas y revisión por el equipo.
        """
        self.partida = None
        self.ultimo_paso_ms = None
        self.algoritmo_seleccionado = None
        try:
            self.vista = cargar_escenario(ruta)
            self.error = None
        except ScenarioValidationError as error:
            self.error = f"Escenario inválido: {error}"
        except json.JSONDecodeError as error:
            self.error = f"JSON inválido: {error}"
        except (OSError, ValueError) as error:
            self.error = f"No se pudo cargar: {error}"

    def _iniciar_partida(self, algoritmo: str) -> None:
        """Crea una partida nueva en la que ambos bandos usan `algoritmo`."""
        try:
            self.partida = nueva_partida(self.vista, algoritmo)
            self.algoritmo_seleccionado = algoritmo
            self.ultimo_paso_ms = None
            self.error = None
        except (ValueError, OSError) as error:
            self.error = f"No se pudo iniciar la partida: {error}"

    def _reiniciar(self) -> None:
        """Vuelve al estado inicial del escenario y deselecciona el algoritmo."""
        if self.vista is None:
            return
        self.partida = None
        self.ultimo_paso_ms = None
        self.algoritmo_seleccionado = None
        self.error = None

    def _actualizar(self) -> None:
        """Ejecuta el siguiente turno cuando ha pasado el intervalo configurado."""
        if self.partida is None or self.partida.terminada:
            return

        ahora = pygame.time.get_ticks()
        if self.ultimo_paso_ms is None or ahora - self.ultimo_paso_ms >= INTERVALO_PASO_MS:
            try:
                self.partida.avanzar()
            except (ValueError, RuntimeError) as error:
                self.error = f"Error en la partida: {error}"
                self.partida = None
                return
            self.ultimo_paso_ms = ahora

    def _progreso_animacion(self):
        """Devuelve (posiciones previas, progreso en [0, 1]) para animar la ficha."""
        if self.partida is None or self.ultimo_paso_ms is None:
            return None, 1.0
        transcurrido = pygame.time.get_ticks() - self.ultimo_paso_ms
        progreso = min(1.0, max(0.0, transcurrido / INTERVALO_PASO_MS))
        return self.partida.posiciones_previas(), progreso

    def ejecutar(self) -> None:
        """Ejecuta el bucle principal hasta cerrar la ventana."""
        try:
            while True:
                self._procesar_eventos()
                self._actualizar()
                self._dibujar()
                self.reloj.tick(60)
        finally:
            pygame.quit()

    def _procesar_eventos(self) -> None:
        """Atiende eventos de cierre, redimensionado y clic en botones."""
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                raise SystemExit
            if evento.type == pygame.VIDEORESIZE:
                self.pantalla = pygame.display.set_mode(
                    (evento.w, evento.h), pygame.RESIZABLE
                )
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if self.boton and self.boton.contiene(evento.pos):
                    ruta = self._elegir_archivo()
                    if ruta:
                        self.cargar(ruta)
                elif self.boton_reiniciar and self.boton_reiniciar.contiene(evento.pos):
                    self._reiniciar()
                elif self.vista is not None:
                    for boton in self.botones_algoritmos:
                        if boton.contiene(evento.pos):
                            self._iniciar_partida(boton.clave)
                            break

    def _elegir_archivo(self) -> str | None:
        """Abre el diálogo nativo para seleccionar un archivo .json."""
        raiz = tkinter.Tk()
        raiz.withdraw()
        raiz.attributes("-topmost", True)
        try:
            ruta = filedialog.askopenfilename(
                title="Cargar escenario",
                filetypes=[("Escenarios JSON", "*.json"), ("Todos", "*.*")],
            )
        finally:
            raiz.destroy()
            pygame.event.clear()

        return ruta or None

    def _dibujar(self) -> None:
        """Dibuja el tablero con el estado actual de la partida y el panel lateral."""
        self.pantalla.fill(renderer.COLOR_FONDO)
        ancho, alto = self.pantalla.get_size()

        rect_panel = panels.calcular_panel(ancho, alto)
        self.boton = panels.construir_boton(rect_panel)
        self.boton_reiniciar = panels.construir_boton_reiniciar(
            rect_panel, self.boton.rect.bottom + 10
        )
        self.botones_algoritmos = panels.construir_botones_algoritmos(
            rect_panel,
            self.boton_reiniciar.rect.bottom + 34,
            self.algoritmos,
        )

        if self.vista is not None:
            layout = renderer.calcular_layout(
                ancho - rect_panel.width,
                alto,
                self.vista.filas,
                self.vista.columnas,
            )
            vista_mostrada = (
                vista_de_estado(self.vista, self.partida.estado)
                if self.partida is not None
                else self.vista
            )
            previas, progreso = self._progreso_animacion()
            anterior = self.partida.anterior if self.partida is not None else None
            recogida = (
                anterior is not None
                and anterior.portador is None
                and self.partida.estado.portador is not None
            )
            renderer.dibujar_tablero(
                self.pantalla,
                vista_mostrada,
                layout,
                self.fuentes,
                self.imagen_recurso,
                previas,
                progreso,
                recogida,
                self.imagenes_terreno,
                self.imagenes_bando,
            )

        textos_partida = self.partida.resumen() if self.partida is not None else ()
        panels.dibujar_panel(
            self.pantalla,
            self.vista,
            rect_panel,
            self.fuentes,
            self.boton,
            self.error,
            self.botones_algoritmos,
            self.algoritmo_seleccionado,
            textos_partida,
            self.boton_reiniciar,
            self.imagenes_terreno,
        )
        pygame.display.flip()
