"""
HUD: Sistema de interfaz de usuario, menús y notificaciones.
"""
import pygame
from src.settings import *

class HUD:
    def __init__(self, screen):
        self.screen = screen
        self.notifications = []
        
        # Fuentes tácticas
        self.font_title = pygame.font.SysFont('monospace', 48, bold=True)
        self.font_subtitle = pygame.font.SysFont('monospace', 22)
        self.font_large = pygame.font.SysFont('monospace', 36, bold=True)
        self.font_normal = pygame.font.SysFont('monospace', 20, bold=True)
        self.font_small = pygame.font.SysFont('monospace', 14)
        
        # Definición geométrica de los botones del menú interactivos
        cx = SCREEN_WIDTH // 2
        cy = SCREEN_HEIGHT // 2
        self.btn_iniciar = pygame.Rect(cx - 125, cy - 10, 250, 50)
        self.btn_controles = pygame.Rect(cx - 125, cy + 60, 250, 50)
        self.btn_salir = pygame.Rect(cx - 125, cy + 130, 250, 50)
        
    def add_notification(self, text, color=(255, 255, 255), duration=3.0):
        self.notifications.append({'text': text, 'color': color, 'timer': duration})
        
    def update(self, dt, global_alert):
        for notif in self.notifications[:]:
            notif['timer'] -= dt
            if notif['timer'] <= 0:
                self.notifications.remove(notif)
                
    def draw(self, global_alert, player_stones, current_zone, fps):
        # 1. Barra de Alerta Global
        pygame.draw.rect(self.screen, (50, 0, 0), (20, 20, 200, 20))
        alert_width = (global_alert / ALERT_MAX) * 200
        color_alert = (255, 0, 0) if global_alert > ALERT_MAX * 0.7 else (255, 150, 0) if global_alert > ALERT_MAX * 0.3 else (0, 255, 0)
        pygame.draw.rect(self.screen, color_alert, (20, 20, alert_width, 20))
        pygame.draw.rect(self.screen, (255, 255, 255), (20, 20, 200, 20), 2)
        
        txt_alert = self.font_small.render(f"ALERTA: {int((global_alert/ALERT_MAX)*100)}%", True, (255, 255, 255))
        self.screen.blit(txt_alert, (25, 22))
        
        # 2. Munición (Piedras)
        txt_stones = self.font_normal.render(f"Piedras: {player_stones}", True, (200, 200, 200))
        self.screen.blit(txt_stones, (20, 50))
        
        # 3. Zona y FPS
        txt_zone = self.font_normal.render(f"Zona: {current_zone}", True, (150, 200, 255))
        self.screen.blit(txt_zone, (SCREEN_WIDTH - 150, 20))
        
        txt_fps = self.font_small.render(f"FPS: {int(fps)}", True, (100, 100, 100))
        self.screen.blit(txt_fps, (SCREEN_WIDTH - 80, 50))
        
        # 4. Notificaciones
        for i, notif in enumerate(self.notifications):
            alpha = min(255, int(notif['timer'] * 255))
            txt = self.font_normal.render(notif['text'], True, notif['color'])
            txt.set_alpha(alpha)
            self.screen.blit(txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 80 + i * 30))

    def _draw_button(self, rect, text, mouse_pos):
        """Dibuja un botón interactivo que reacciona si el ratón pasa por encima."""
        color_normal = (30, 40, 50)
        color_hover = (60, 80, 100)
        color_text = (200, 220, 255)
        
        # Efecto Hover si el cursor está sobre el rectángulo
        if rect.collidepoint(mouse_pos):
            pygame.draw.rect(self.screen, color_hover, rect, border_radius=5)
            pygame.draw.rect(self.screen, (100, 150, 255), rect, 2, border_radius=5)
        else:
            pygame.draw.rect(self.screen, color_normal, rect, border_radius=5)
            pygame.draw.rect(self.screen, (50, 70, 90), rect, 2, border_radius=5)
            
        img_text = self.font_normal.render(text, True, color_text)
        self.screen.blit(img_text, img_text.get_rect(center=rect.center))

    def draw_menu(self):
        """Pantalla principal limpia y directa."""
        self.screen.fill((10, 10, 15)) 
        mouse_pos = pygame.mouse.get_pos()
        
        # Textos solicitados intactos
        title = self.font_title.render("SOMBRAS EN LA UNMSM", True, (255, 50, 50))
        subtitle = self.font_subtitle.render("INFILTRACION TACTICA NOCTURNA", True, (150, 150, 150))
        
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 120)))
        self.screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 70)))
        
        # Renderizado de botones interactivos
        self._draw_button(self.btn_iniciar, "INICIAR", mouse_pos)
        self._draw_button(self.btn_controles, "CONTROLES", mouse_pos)
        self._draw_button(self.btn_salir, "SALIR", mouse_pos)

    def draw_controls(self):
        """Pantalla que se abre al hacer clic en 'CONTROLES'."""
        self.screen.fill((10, 10, 15))
        
        title = self.font_large.render("CONTROLES", True, (200, 200, 255))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 100)))
        
        controls = [
            "W, A, S, D o Flechas : Moverse",
            "ESPACIO              : Ocultarse / Cobertura",
            "CLIC DERECHO         : Lanzar piedra",
            "TECLA Q              : Activar alarma de auto",
            "ESC                  : Pausar juego"
        ]
        
        for i, text in enumerate(controls):
            txt = self.font_normal.render(text, True, (180, 180, 180))
            self.screen.blit(txt, (SCREEN_WIDTH//2 - 220, 200 + i * 40))
            
        volver = self.font_normal.render("Presiona ESC o HAZ CLIC para volver", True, (100, 100, 100))
        self.screen.blit(volver, volver.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 100)))

    def draw_game_over(self, reason):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((50, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        title = self.font_title.render("GAME OVER", True, (255, 50, 50))
        sub = self.font_large.render(reason, True, (200, 150, 150))
        restart = self.font_normal.render("Presiona 'R' para reiniciar", True, (255, 255, 255))
        
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50)))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 10)))
        self.screen.blit(restart, restart.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 80)))
        
    def draw_win(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 50, 0, 150))
        self.screen.blit(overlay, (0, 0))
        
        title = self.font_title.render("¡ESCAPASTE!", True, (50, 255, 50))
        sub = self.font_normal.render("Lograste salir por la Puerta 7.", True, (200, 255, 200))
        
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20)))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 30)))
