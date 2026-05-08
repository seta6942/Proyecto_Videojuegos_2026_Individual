"""
Sistema de iluminación nocturna.
El mapa se ve como de noche (oscuro, azulado) PERO no es negro:
siempre hay luz ambiente para que el jugador pueda ver el campus.
Faroles y linterna del jugador iluminan más fuerte sus zonas.
"""
import pygame
import math
from src.settings import (
    NIGHT_AMBIENT, LAMP_RADIUS, PLAYER_LIGHT_RADIUS,
    ALERT_HIGH_THRESHOLD,
)


class LightingSystem:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Capa de luz: se rellena con el ambiente nocturno (gris azulado)
        # y luego se le SUMAN las luces para crear puntos brillantes.
        # Al final se aplica con BLEND_RGBA_MULT sobre la pantalla.
        self.light_surface = pygame.Surface((screen_width, screen_height))

        # Cache de gradientes radiales (por radio + color) para no
        # generarlos cada frame.
        self._gradient_cache = {}

        # Animación de faroles (parpadeo suave, individual)
        self.flicker_timer = 0.0
        self.flicker_phases = {}

    def render(self, screen, camera, lamp_positions, player_pos, global_alert):
        """Renderiza el sistema de iluminación nocturna."""
        self.flicker_timer += 0.016  # ~60fps

        # 1) Ambiente nocturno: ligeramente más oscuro si la alerta es alta
        ar, ag, ab = NIGHT_AMBIENT
        if global_alert >= ALERT_HIGH_THRESHOLD:
            ar = max(40, ar - 15)
            ag = max(40, ag - 15)
            ab = max(60, ab - 15)
        self.light_surface.fill((ar, ag, ab))

        # 2) Linterna del jugador (cálida, fuerte)
        player_sx, player_sy = camera.world_to_screen(player_pos.x, player_pos.y)
        self._add_light(player_sx, player_sy, PLAYER_LIGHT_RADIUS,
                        (220, 210, 180))

        # 3) Faroles del campus (anaranjados, parpadeo sutil)
        for lx, ly in lamp_positions:
            sx, sy = camera.world_to_screen(lx, ly)
            if (-LAMP_RADIUS <= sx <= self.screen_width + LAMP_RADIUS and
                -LAMP_RADIUS <= sy <= self.screen_height + LAMP_RADIUS):
                key = (int(lx), int(ly))
                if key not in self.flicker_phases:
                    self.flicker_phases[key] = (hash(key) % 100) / 100.0
                phase = self.flicker_timer * 2.3 + self.flicker_phases[key] * 6.28
                flicker = 1.0 + math.sin(phase) * 0.05
                radius = int(LAMP_RADIUS * flicker)
                self._add_light(sx, sy, radius, (255, 190, 110))

        # 4) Aplicar la capa de luz al mapa (multiplicación)
        screen.blit(self.light_surface, (0, 0),
                    special_flags=pygame.BLEND_RGBA_MULT)

    def _add_light(self, cx, cy, radius, color):
        """Suma un gradiente radial de luz a la capa de iluminación."""
        if radius <= 0:
            return
        grad = self._get_gradient(radius, color)
        self.light_surface.blit(
            grad, (int(cx - radius), int(cy - radius)),
            special_flags=pygame.BLEND_RGB_ADD,
        )

    def _get_gradient(self, radius, color):
        """Devuelve (con caché) un círculo con gradiente del centro al borde."""
        key = (radius, color)
        if key in self._gradient_cache:
            return self._gradient_cache[key]

        size = radius * 2
        surf = pygame.Surface((size, size))
        surf.set_colorkey((0, 0, 0))
        cr, cg, cb = color
        # Dibujamos círculos concéntricos del más grande (tenue) al más
        # pequeño (intenso), creando un gradiente suave.
        steps = max(8, radius // 4)
        for i in range(steps, 0, -1):
            ratio = i / steps
            r = int(radius * ratio)
            if r <= 0:
                continue
            # intensidad cae cuadráticamente hacia el borde
            intensity = (1.0 - ratio) ** 1.6
            ir = int(cr * intensity)
            ig = int(cg * intensity)
            ib = int(cb * intensity)
            pygame.draw.circle(surf, (ir, ig, ib), (radius, radius), r)
        self._gradient_cache[key] = surf
        return surf

    def render_lamppost(self, screen, camera, lamp_positions):
        """Dibuja el poste del farol visible (sprite simple)."""
        for lx, ly in lamp_positions:
            sx, sy = camera.world_to_screen(int(lx), int(ly))
            if -20 <= sx <= self.screen_width + 20 and -20 <= sy <= self.screen_height + 20:
                # Poste vertical
                pygame.draw.line(screen, (90, 90, 95), (sx, sy), (sx, sy + 22), 2)
                # Cabeza del farol
                pygame.draw.ellipse(screen, (210, 170, 70), (sx - 6, sy - 4, 12, 6))
                # Bombilla (siempre visible)
                pygame.draw.circle(screen, (255, 220, 130), (sx, sy - 1), 3)
