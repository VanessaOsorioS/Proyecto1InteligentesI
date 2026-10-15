"""Aplicación pygame: ventana, bucle principal y carga de escenarios."""

import json
import os

import pygame
import tkinter
from tkinter import filedialog

from tacticalgrid.app.controller import cargar_escenario, ScenarioVista
from tacticalgrid.io.scenario_validator import ScenarioValidationError
from tacticalgrid.ui import panels, renderer


class PygameApp:
    """Ventana de visualización del tablero con botón para cargar JSON."""

    def __init__(self, ruta_inicial: str | None = None, tamano=(1100, 720)):
        pygame.init()
        pygame.display.set_caption("TacticalGrid")
        self.pantalla = pygame.display.set_mode(tamano, pygame.RESIZABLE)
        self.reloj = pygame.time.Clock()

        self.imagen_recurso = None
        ruta_bandera = os.path.join(
            os.path.dirname(__file__), "assets", "bandera_recurso.png"
        )
        try:
            self.imagen_recurso = pygame.image.load(ruta_bandera).convert_alpha()
        except (pygame.error, FileNotFoundError):
            self.imagen_recurso = None

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

        if ruta_inicial and os.path.exists(ruta_inicial):
            self.cargar(ruta_inicial)

    def cargar(self, ruta: str) -> None:
        """
        Purpose:
            Cargar un escenario y dejarlo listo para dibujar.

        Preconditions:
            `ruta` es una ruta de archivo JSON.

        Postconditions:
            Actualiza `self.vista` o `self.error` según el resultado.

        Complexity:
            O(F * C + U), la del cargador del escenario.

        AI usage: Yes
        AI intervention:
            Manejo de errores propuesto con asistencia de IA.
        Student validation:
            Pendiente de pruebas y revisión por el equipo.
        """
        try:
            self.vista = cargar_escenario(ruta)
            self.error = None
        except ScenarioValidationError as error:
            self.error = f"Escenario inválido: {error}"
        except json.JSONDecodeError as error:
            self.error = f"JSON inválido: {error}"
        except (OSError, ValueError) as error:
            self.error = f"No se pudo cargar: {error}"

    def ejecutar(self) -> None:
        """Ejecuta el bucle principal hasta cerrar la ventana."""
        try:
            while True:
                self._procesar_eventos()
                self._dibujar()
                self.reloj.tick(60)
        finally:
            pygame.quit()

    def _procesar_eventos(self) -> None:
        """Atiende eventos de cierre, redimensionado y clic del botón."""
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
        """Dibuja el tablero y el panel lateral, y refresca la pantalla."""
        self.pantalla.fill(renderer.COLOR_FONDO)
        ancho, alto = self.pantalla.get_size()

        rect_panel = panels.calcular_panel(ancho, alto)
        self.boton = panels.construir_boton(rect_panel)

        if self.vista is not None:
            layout = renderer.calcular_layout(
                ancho - rect_panel.width,
                alto,
                self.vista.filas,
                self.vista.columnas,
            )
            renderer.dibujar_tablero(
                self.pantalla,
                self.vista,
                layout,
                self.fuentes,
                self.imagen_recurso,
            )

        panels.dibujar_panel(
            self.pantalla,
            self.vista,
            rect_panel,
            self.fuentes,
            self.boton,
            self.error,
        )
        pygame.display.flip()
