"""
HUD (Heads-Up Display) del juego.
Muestra la Alerta Global, inventario de piedras, zona actual y mensajes.
"""
import pygame
import math
from src.settings import *


class HUD:
    def __init__(self, screen):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        
        # Fuentes
        self.font_title = pygame.font.SysFont('monospace', 20, bold=True)
        self.font_normal = pygame.font.SysFont('monospace', 14)
        self.font_small = pygame.font.SysFont('monospace', 12)
        self.font_large = pygame.font.SysFont('monospace', 32, bold=True)
        
        # Mensajes de notificación
        self.notifications = []
        self.max_notifications = 3
        
        # Animación de alerta
        self.alert_pulse = 0.0
    
    def add_notification(self, text, color=(255, 255, 100), duration=3.0):
        """Agrega un mensaje temporal en pantalla."""
        self.notifications.append({
            'text': text,
            'color': color,
            'timer': duration,
            'max_time': duration
        })
        if len(self.notifications) > self.max_notifications:
            self.notifications.pop(0)
    
    def update(self, dt, global_alert):
        """Actualiza animaciones del HUD."""
        # Pulsar si alerta alta
        if global_alert >= ALERT_HIGH_THRESHOLD:
            self.alert_pulse += dt * 5
        else:
            self.alert_pulse += dt * 2
        
        # Actualizar notificaciones
        for notif in self.notifications[:]:
            notif['timer'] -= dt
            if notif['timer'] <= 0:
                self.notifications.remove(notif)
    
    def draw(self, global_alert, player_stones, current_zone, fps=0):
        """Dibuja el HUD completo."""
        self._draw_alert_bar(global_alert)
        self._draw_stones(player_stones)
        self._draw_zone_indicator(current_zone)
        self._draw_controls_hint()
        self._draw_notifications()
        if fps > 0:
            self._draw_fps(fps)
    
    def _draw_alert_bar(self, global_alert):
        """Barra de Alerta Global en la parte superior."""
        bar_w = 350
        bar_h = 22
        bar_x = self.width // 2 - bar_w // 2
        bar_y = 12
        
        # Fondo de la barra
        bg_surf = pygame.Surface((bar_w + 4, bar_h + 4), pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, (0, 0, 0, 160), (0, 0, bar_w + 4, bar_h + 4), border_radius=4)
        self.screen.blit(bg_surf, (bar_x - 2, bar_y - 2))
        
        # Color de la barra según nivel
        if global_alert < ALERT_MED_THRESHOLD:
            bar_color = (0, 200, 50)
        elif global_alert < ALERT_HIGH_THRESHOLD:
            t = (global_alert - ALERT_MED_THRESHOLD) / (ALERT_HIGH_THRESHOLD - ALERT_MED_THRESHOLD)
            bar_color = (
                int(0 + 255 * t),
                int(200 - 140 * t),
                0
            )
        else:
            # Pulso rojo cuando está alta
            pulse = abs(math.sin(self.alert_pulse))
            intensity = int(150 + 105 * pulse)
            bar_color = (intensity, 0, 0)
        
        fill_w = int(bar_w * global_alert / 100)
        if fill_w > 0:
            pygame.draw.rect(self.screen, bar_color, (bar_x, bar_y, fill_w, bar_h), border_radius=3)
        
        # Borde
        pygame.draw.rect(self.screen, (150, 150, 150), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=3)
        
        # Texto
        label = self.font_normal.render("ALERTA GLOBAL", True, (220, 220, 220))
        pct_text = self.font_normal.render(f"{int(global_alert)}%", True, (255, 255, 255))
        self.screen.blit(label, (bar_x + 4, bar_y + 3))
        self.screen.blit(pct_text, (bar_x + bar_w - 38, bar_y + 3))
        
        # Marcadores de umbral
        for threshold, color in [(ALERT_MED_THRESHOLD, (255, 220, 0)), (ALERT_HIGH_THRESHOLD, (255, 60, 0))]:
            tx = bar_x + int(bar_w * threshold / 100)
            pygame.draw.line(self.screen, color, (tx, bar_y), (tx, bar_y + bar_h), 2)
        
        # Título del juego pequeño
        title_surf = self.font_small.render("SOMBRAS EN LA UNMSM", True, (180, 150, 220))
        self.screen.blit(title_surf, (bar_x, bar_y + bar_h + 3))
    
    def _draw_stones(self, stones):
        """Muestra el inventario de piedras (clic der. para lanzar)."""
        x, y = 12, 12
        
        bg = pygame.Surface((90, 50), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 140), (0, 0, 90, 50), border_radius=4)
        self.screen.blit(bg, (x, y))
        
        label = self.font_small.render("PIEDRAS", True, (180, 180, 180))
        self.screen.blit(label, (x + 5, y + 4))
        
        for i in range(STONE_MAX):
            cx = x + 12 + i * 22
            cy = y + 28
            if i < stones:
                pygame.draw.circle(self.screen, (160, 140, 100), (cx, cy), 7)
                pygame.draw.circle(self.screen, (190, 170, 130), (cx - 2, cy - 2), 3)
            else:
                pygame.draw.circle(self.screen, (60, 60, 60), (cx, cy), 7, 1)
    
    def _draw_zone_indicator(self, zone):
        """Muestra la zona actual."""
        if zone not in ZONES:
            return
        
        zone_data = ZONES[zone]
        x = self.width - 10
        y = 12
        
        zone_name = zone_data['name']
        text = f"ZONA {zone}: {zone_name}"
        
        surf = self.font_small.render(text, True, (220, 220, 220))
        bg_w = surf.get_width() + 16
        bg_h = surf.get_height() + 10
        
        bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 140), (0, 0, bg_w, bg_h), border_radius=4)
        color = zone_data['color']
        pygame.draw.rect(bg, (*color, 100), (0, 0, bg_w, bg_h), border_radius=4)
        pygame.draw.rect(bg, (*color, 200), (0, 0, bg_w, bg_h), 1, border_radius=4)
        
        self.screen.blit(bg, (x - bg_w, y))
        self.screen.blit(surf, (x - surf.get_width() - 8, y + 5))
    
    def _draw_controls_hint(self):
        """Muestra controles básicos en la esquina inferior izquierda."""
        hints = [
            "WASD: Mover",
            "SHIFT: Sigilo",
            "SPACE: Ocultarse",
            "CLIC DER: Piedra",
            "Q: Alarma auto",
            "E: Panel cámara",
        ]
        
        bg_h = len(hints) * 16 + 10
        bg = pygame.Surface((130, bg_h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 120), (0, 0, 130, bg_h), border_radius=4)
        self.screen.blit(bg, (8, self.height - bg_h - 8))
        
        for i, hint in enumerate(hints):
            surf = self.font_small.render(hint, True, (160, 160, 160))
            self.screen.blit(surf, (14, self.height - bg_h - 8 + 5 + i * 16))
    
    def _draw_notifications(self):
        """Muestra notificaciones temporales en el centro-derecho."""
        base_x = self.width - 10
        base_y = self.height - 80
        
        for i, notif in enumerate(self.notifications):
            alpha_ratio = min(1.0, notif['timer'] / 0.5)
            alpha = int(255 * alpha_ratio)
            
            surf = self.font_normal.render(notif['text'], True, notif['color'])
            surf.set_alpha(alpha)
            
            self.screen.blit(surf, (base_x - surf.get_width(), base_y - i * 24))
    
    def _draw_fps(self, fps):
        surf = self.font_small.render(f"FPS: {fps:.0f}", True, (100, 100, 100))
        self.screen.blit(surf, (self.width - surf.get_width() - 8, self.height - 18))
    
    def draw_game_over(self, reason="REFUERZOS LLEGARON"):
        """Pantalla de Game Over."""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((150, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        
        go_surf = self.font_large.render("GAME OVER", True, (255, 255, 255))
        sub_surf = self.font_title.render(reason, True, (255, 220, 180))
        hint_surf = self.font_normal.render("Presiona R para reiniciar  |  ESC para salir", True, (200, 200, 200))
        
        cx = self.width // 2
        cy = self.height // 2
        
        self.screen.blit(go_surf, go_surf.get_rect(center=(cx, cy - 50)))
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(cx, cy)))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(cx, cy + 50)))
    
    def draw_win(self):
        """Pantalla de victoria."""
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 100, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        win_surf = self.font_large.render("!ESCAPASTE!", True, (100, 255, 100))
        sub_surf = self.font_title.render("Melvin llego a la Puerta 7", True, (200, 255, 200))
        hint_surf = self.font_normal.render("Presiona R para jugar de nuevo  |  ESC para salir", True, (180, 220, 180))
        
        cx = self.width // 2
        cy = self.height // 2
        
        self.screen.blit(win_surf, win_surf.get_rect(center=(cx, cy - 50)))
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(cx, cy)))
        self.screen.blit(hint_surf, hint_surf.get_rect(center=(cx, cy + 50)))
    
    def draw_menu(self):
        """Pantalla de menú principal."""
        self.screen.fill(COLOR_BACKGROUND)
        
        # Título
        title1 = self.font_large.render("SOMBRAS EN LA UNMSM", True, (180, 100, 220))
        title2 = self.font_title.render("Infiltración Táctica Nocturna", True, (120, 180, 255))
        
        sub = self.font_normal.render("Ciudad Universitaria de la UNMSM — Noche — Zona de Exclusión", True, (160, 160, 160))
        inst = self.font_normal.render("Presiona ENTER para comenzar  |  ESC para salir", True, (200, 200, 200))
        
        # Créditos
        credit = self.font_small.render("Tapia Acosta Sandro Estanislao — FCM-UNMSM — 2026", True, (120, 100, 140))
        
        cx = self.width // 2
        cy = self.height // 2
        
        self.screen.blit(title1, title1.get_rect(center=(cx, cy - 120)))
        self.screen.blit(title2, title2.get_rect(center=(cx, cy - 75)))
        
        # Separador
        pygame.draw.line(self.screen, (80, 40, 120), (cx - 300, cy - 50), (cx + 300, cy - 50), 1)
        
        # Descripción del juego
        lines = [
            "Melvin, estudiante de Computacion Cientifica, se quedo dormido en el",
            "parque de la Fac. Quimica. El campus cerro. La seguridad lo busca.",
            "Todas las puertas estan cerradas... menos la Puerta 7.",
            "",
            "Cruza las 4 zonas del campus evitando a los guardias.",
        ]
        for i, line in enumerate(lines):
            surf = self.font_small.render(line, True, (200, 185, 220))
            self.screen.blit(surf, surf.get_rect(center=(cx, cy - 25 + i * 18)))
        
        self.screen.blit(sub, sub.get_rect(center=(cx, cy + 80)))
        self.screen.blit(inst, inst.get_rect(center=(cx, cy + 110)))
        self.screen.blit(credit, credit.get_rect(center=(cx, self.height - 20)))
