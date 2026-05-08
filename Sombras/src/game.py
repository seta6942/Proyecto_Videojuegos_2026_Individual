"""
Game: Clase principal del juego Sombras en la UNMSM.
Maneja el loop principal, estados del juego y coordinación de subsistemas.
"""
import pygame
import sys
import math
import random
from src.settings import *
from src.map_generator import ProceduralMap, total_levels
from src.camera import Camera
from src.player import Player
from src.guard import Guard
from src.hud import HUD
from src.lighting import LightingSystem
from src.sprites import SpriteGenerator


class Stone:
    """Efecto visual de una piedra lanzada."""
    def __init__(self, start, end):
        self.start = pygame.math.Vector2(start)
        self.end   = pygame.math.Vector2(end)
        self.pos   = pygame.math.Vector2(start)
        self.progress = 0.0
        self.speed = 3.0
        self.active = True
        
        direction = self.end - self.start
        dist = direction.length()
        self.travel_time = dist / 200.0
        self.elapsed = 0.0
        
        self.distracted = False  # ya distrajó guardias
    
    def update(self, dt):
        self.elapsed += dt
        t = min(1.0, self.elapsed / max(self.travel_time, 0.001))
        self.pos = self.start.lerp(self.end, t)
        
        if t >= 1.0:
            self.active = False  # llegó al destino (sigue visible como punto de impacto)
        
        return t >= 1.0  # retorna True cuando llega


class CarAlarm:
    """Alarma de auto activada."""
    def __init__(self, pos):
        self.pos = pygame.math.Vector2(pos)
        self.timer = CAR_ALARM_TIME
        self.active = True
        self.blink = 0.0
    
    def update(self, dt):
        self.timer -= dt
        self.blink += dt * 6
        if self.timer <= 0:
            self.active = False


class Game:
    """Loop principal del juego."""
    
    STATE_MENU     = 'menu'
    STATE_PLAYING  = 'playing'
    STATE_GAMEOVER = 'gameover'
    STATE_WIN      = 'win'
    STATE_PAUSED   = 'paused'
    
    def __init__(self):
        pygame.init()
        pygame.font.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        
        self.clock = pygame.time.Clock()
        self.state = self.STATE_MENU
        self.running = True
        
        # Inicializar subsistemas
        self.sprite_gen = SpriteGenerator()
        self._init_game()
    
    def _init_game(self):
        """Inicializa/reinicia el juego desde el Nivel 1."""
        self.current_level = 1
        self.lighting = LightingSystem(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.hud = HUD(self.screen)
        self._load_level(self.current_level, first=True)

    def _load_level(self, level_number, first=False):
        """Carga el nivel indicado: mapa, jugador y guardias."""
        self.map = ProceduralMap(level_number=level_number)
        self.camera = Camera(self.map.pixel_width, self.map.pixel_height)

        spawn = self.map.spawn_point
        if first:
            self.player = Player(spawn.x, spawn.y, self.sprite_gen)
        else:
            # Conserva piedras restantes y estado del jugador entre niveles
            self.player.pos = pygame.math.Vector2(spawn.x, spawn.y)
            self.player.is_hiding = False

        self.camera.offset_x = max(0, spawn.x - SCREEN_WIDTH // 2)
        self.camera.offset_y = max(0, spawn.y - SCREEN_HEIGHT // 2)

        # Guardias del nivel actual
        self.guards = []
        for i, gdata in enumerate(self.map.guard_spawns):
            guard = Guard(
                gdata['pos'].x, gdata['pos'].y,
                gdata['patrol'],
                gdata['zone'],
                self.sprite_gen,
                guard_id=i,
            )
            self.guards.append(guard)

        # Reset del estado dinámico del nivel
        self.global_alert = 0.0
        self.stones_active = []
        self.stone_impacts = []
        self.car_alarms = []
        self.active_car_ids = set()
        self.current_zone = level_number
        self.gameover_reason = ""
        self.screen_flash = 0.0
        self.flash_color = (255, 0, 0)

        # Aviso por pantalla
        self.hud.add_notification(self.map.level_name, (255, 230, 130))
        self.hud.add_notification(self.map.level_hint, (180, 220, 255))

    def _advance_level(self):
        """Avanza al siguiente nivel; si es el último, victoria."""
        if self.map.is_final_level():
            self.state = self.STATE_WIN
            return
        self.current_level += 1
        self._load_level(self.current_level, first=False)

    def run(self):
        """Loop principal del juego."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # cap para evitar saltos
            
            self._handle_events()
            self._update(dt)
            self._draw()
        
        pygame.quit()
        sys.exit()
    
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == self.STATE_PLAYING:
                        self.state = self.STATE_PAUSED
                    elif self.state == self.STATE_PAUSED:
                        self.state = self.STATE_PLAYING
                    else:
                        self.running = False
                
                if event.key == pygame.K_RETURN and self.state == self.STATE_MENU:
                    self.state = self.STATE_PLAYING
                
                if event.key == pygame.K_r and self.state in (self.STATE_GAMEOVER, self.STATE_WIN):
                    self._init_game()
                    self.state = self.STATE_PLAYING
                
                if event.key == pygame.K_r and self.state == self.STATE_PAUSED:
                    self._init_game()
                    self.state = self.STATE_PLAYING
                
                if self.state == self.STATE_PLAYING:
                    # Espacio = ocultarse
                    if event.key == pygame.K_SPACE:
                        self.player.is_hiding = not self.player.is_hiding
                        if self.player.is_hiding:
                            self.hud.add_notification("Oculto!", (100, 200, 255))
                        else:
                            self.hud.add_notification("Visible", (200, 200, 100))
                    
                    # Q = alarma de auto (más cercano)
                    if event.key == pygame.K_q:
                        self._activate_nearest_car()
                
                if event.key == pygame.K_F1:
                    # Debug info
                    self.hud.add_notification(
                        f"Pos: {int(self.player.pos.x//TILE_SIZE)}, {int(self.player.pos.y//TILE_SIZE)}",
                        (200, 200, 200)
                    )
            
            # Clic derecho = lanzar piedra
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3 and self.state == self.STATE_PLAYING:
                    mouse_x, mouse_y = event.pos
                    world_x, world_y = self.camera.screen_to_world(mouse_x, mouse_y)
                    impact = self.player.throw_stone(world_x, world_y)
                    
                    if impact is not None:
                        stone = Stone(self.player.pos, impact)
                        self.stones_active.append(stone)
                        self.hud.add_notification(f"Piedra! ({self.player.stones} restantes)", (220, 200, 100))
                    elif self.player.stones <= 0:
                        self.hud.add_notification("Sin piedras!", (255, 100, 100))
    
    def _activate_nearest_car(self):
        """Activa la alarma del auto más cercano al jugador."""
        best_car = None
        best_dist = CAR_ALARM_RADIUS * 2
        best_idx = -1
        
        for i, car_pos in enumerate(self.map.car_positions):
            if i in self.active_car_ids:
                continue
            dist = (car_pos - self.player.pos).length()
            if dist < best_dist:
                best_dist = dist
                best_car = car_pos
                best_idx = i
        
        if best_car and best_dist <= CAR_ALARM_RADIUS:
            self.active_car_ids.add(best_idx)
            alarm = CarAlarm(best_car)
            self.car_alarms.append(alarm)
            self.hud.add_notification("!Alarma de auto activada!", (255, 180, 50))
            
            # Distraer guardias cercanos
            for guard in self.guards:
                if (guard.pos - best_car).length() <= CAR_ALARM_RADIUS:
                    guard.distract_to(best_car, CAR_ALARM_TIME)
        elif best_car:
            self.hud.add_notification("Demasiado lejos del auto", (180, 100, 100))
        else:
            self.hud.add_notification("No hay autos disponibles", (180, 100, 100))
    
    def _update(self, dt):
        if self.state != self.STATE_PLAYING:
            if self.state == self.STATE_MENU:
                pass  # animaciones de menú si las hay
            return
        
        # Input del jugador
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        
        # Actualizar jugador con colisiones
        self.player.update(dt, self.map.collision_rects)
        
        # Actualizar cámara
        self.camera.update(self.player.pos)
        
        # Zona actual
        self.current_zone = self.map.get_zone_at(self.player.pos.x, self.player.pos.y)
        
        # Actualizar guardias
        seen_count = 0
        heard_count = 0
        caught = False
        caught_by = None
        
        for guard in self.guards:
            can_see, can_hear = guard.update(
                dt, self.player, self.global_alert,
                self.map.collision_rects, self.guards
            )
            if can_see:
                seen_count += 1
            if can_hear:
                heard_count += 1
            
            # ¿Atrapó al jugador?
            if guard.catches_player(self.player):
                caught = True
                caught_by = guard
        
        # Actualizar Alerta Global
        if seen_count > 0:
            self.global_alert += ALERT_RISE_SEEN * seen_count * dt
            self.screen_flash = min(1.0, self.screen_flash + dt * 3)
            self.flash_color = (255, 0, 0)
        elif heard_count > 0:
            self.global_alert += ALERT_RISE_HEARD * dt
        else:
            self.global_alert = max(0, self.global_alert - ALERT_FALL * dt)
        
        self.global_alert = min(ALERT_MAX, self.global_alert)
        
        # Decaer flash
        self.screen_flash = max(0, self.screen_flash - dt * 2)
        
        # Actualizar piedras
        for stone in self.stones_active[:]:
            arrived = stone.update(dt)
            if arrived and not stone.distracted:
                stone.distracted = True
                # Distraer guardias cercanos al impacto
                for guard in self.guards:
                    if (guard.pos - stone.end).length() <= STONE_DISTRACT_RADIUS:
                        guard.distract_to(stone.end, STONE_DISTRACT_TIME)
                self.hud.add_notification("Guardias distraidos!", (200, 255, 100))
        
        # Limpiar piedras viejas
        self.stones_active = [s for s in self.stones_active if s.elapsed < 3.0]
        
        # Actualizar alarmas de auto
        for alarm in self.car_alarms[:]:
            alarm.update(dt)
            if not alarm.active:
                self.car_alarms.remove(alarm)
        
        # Actualizar HUD
        self.hud.update(dt, self.global_alert)
        
        # === CONDICIONES DE FIN DE JUEGO ===
        
        # Game Over: alerta al 100%
        if self.global_alert >= ALERT_MAX:
            self.state = self.STATE_GAMEOVER
            self.gameover_reason = "REFUERZOS LLEGARON"
            return
        
        # Game Over: atrapado
        if caught:
            self.state = self.STATE_GAMEOVER
            self.gameover_reason = "TE ATRAPARON"
            return
        
        # Salida de nivel: avanzar o ganar (en el último nivel = Puerta 7)
        if self.map.exit_rect.collidepoint(self.player.pos.x, self.player.pos.y):
            self._advance_level()
    
    def _draw(self):
        self.screen.fill(COLOR_BACKGROUND)
        
        if self.state == self.STATE_MENU:
            self.hud.draw_menu()
        
        elif self.state in (self.STATE_PLAYING, self.STATE_GAMEOVER, self.STATE_WIN, self.STATE_PAUSED):
            # === MAPA ===
            self.map.draw(self.screen, self.camera)
            
            # === AUTOS ===
            self._draw_cars()
            
            # === GUARDIAS ===
            for guard in self.guards:
                guard.draw(self.screen, self.camera)
            
            # === PIEDRAS EN VUELO ===
            self._draw_stones()
            
            # === JUGADOR ===
            self.player.draw(self.screen, self.camera)
            
            # === EXIT INDICATOR ===
            self._draw_exit_indicator()
            
            # === ILUMINACIÓN NOCTURNA ===
            self.lighting.render_lamppost(self.screen, self.camera, self.map.lamp_positions)
            self.lighting.render(
                self.screen, self.camera,
                self.map.lamp_positions,
                self.player.pos,
                self.global_alert
            )
            
            # === FLASH DE DETECCIÓN ===
            if self.screen_flash > 0:
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                alpha = int(80 * self.screen_flash)
                flash_surf.fill((*self.flash_color, alpha))
                self.screen.blit(flash_surf, (0, 0))
            
            # === HUD ===
            if self.state == self.STATE_PLAYING or self.state == self.STATE_PAUSED:
                fps = self.clock.get_fps()
                self.hud.draw(self.global_alert, self.player.stones, self.current_zone, fps)
            
            # === PANTALLAS ESPECIALES ===
            if self.state == self.STATE_GAMEOVER:
                self.hud.draw_game_over(self.gameover_reason)
            elif self.state == self.STATE_WIN:
                self.hud.draw_win()
            elif self.state == self.STATE_PAUSED:
                self._draw_pause()
        
        pygame.display.flip()
    
    def _draw_cars(self):
        """Dibuja autos en el estacionamiento."""
        car_colors = [
            (120, 120, 140),
            (100, 80, 60),
            (60, 80, 100),
            (140, 90, 70),
            (80, 100, 80),
        ]
        
        for i, car_pos in enumerate(self.map.car_positions):
            sx, sy = self.camera.world_to_screen(int(car_pos.x), int(car_pos.y))
            if not (-50 <= sx <= SCREEN_WIDTH + 50 and -50 <= sy <= SCREEN_HEIGHT + 50):
                continue
            
            color = car_colors[i % len(car_colors)]
            
            # Sombra
            pygame.draw.ellipse(self.screen, (0, 0, 0, 80), (sx - 18, sy + 8, 36, 10))
            
            # Carrocería
            pygame.draw.rect(self.screen, color, (sx - 14, sy - 8, 28, 18), border_radius=3)
            
            # Ventanas
            pygame.draw.rect(self.screen, (50, 80, 120), (sx - 9, sy - 6, 18, 10), border_radius=2)
            
            # Alarma activa = parpadeo naranja
            active = i in self.active_car_ids
            for alarm in self.car_alarms:
                if (alarm.pos - car_pos).length() < 5:
                    blink_on = int(alarm.blink) % 2 == 0
                    if blink_on:
                        pygame.draw.rect(self.screen, (255, 150, 0), (sx - 14, sy - 8, 28, 18), 2, border_radius=3)
                        # Radio de alarma visible
                        alarm_surf = pygame.Surface((CAR_ALARM_RADIUS*2, CAR_ALARM_RADIUS*2), pygame.SRCALPHA)
                        pygame.draw.circle(alarm_surf, (255, 150, 0, 20),
                                         (CAR_ALARM_RADIUS, CAR_ALARM_RADIUS), CAR_ALARM_RADIUS)
                        self.screen.blit(alarm_surf, (sx - CAR_ALARM_RADIUS, sy - CAR_ALARM_RADIUS))
    
    def _draw_stones(self):
        """Dibuja las piedras en vuelo."""
        for stone in self.stones_active:
            sx, sy = self.camera.world_to_screen(int(stone.pos.x), int(stone.pos.y))
            
            # Piedra
            pygame.draw.circle(self.screen, (160, 140, 100), (sx, sy), 4)
            pygame.draw.circle(self.screen, (190, 170, 130), (sx - 1, sy - 1), 2)
            
            # Si llegó, mostrar radio de distracción
            if not stone.active:
                end_sx, end_sy = self.camera.world_to_screen(int(stone.end.x), int(stone.end.y))
                r = STONE_DISTRACT_RADIUS
                
                # Círculo de distracción
                dist_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(dist_surf, (200, 200, 100, 30), (r, r), r)
                pygame.draw.circle(dist_surf, (200, 200, 100, 100), (r, r), r, 1)
                self.screen.blit(dist_surf, (end_sx - r, end_sy - r))
                
                # Símbolo de impacto
                pygame.draw.circle(self.screen, (220, 200, 120), (end_sx, end_sy), 4)
    
    def _draw_exit_indicator(self):
        """Dibuja un indicador de la Puerta 7 en pantalla."""
        exit_rect = self.map.exit_rect
        exit_cx = exit_rect.centerx
        exit_cy = exit_rect.centery
        
        ex, ey = self.camera.world_to_screen(exit_cx, exit_cy)
        
        # Si la salida está en pantalla, dibujar marcador
        if 0 <= ex <= SCREEN_WIDTH and 0 <= ey <= SCREEN_HEIGHT:
            # Efecto de brillo en la salida
            t = pygame.time.get_ticks() / 500.0
            glow_a = int(80 + 60 * math.sin(t))
            glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (0, 255, 80, glow_a), (0, 0, 60, 60), border_radius=4)
            self.screen.blit(glow_surf, (ex - 30, ey - 30))
            
            font = pygame.font.SysFont('monospace', 11, bold=True)
            txt = font.render("PUERTA 7", True, (0, 255, 100))
            self.screen.blit(txt, (ex - txt.get_width()//2, ey - 40))
        else:
            # Flecha apuntando hacia la salida
            dx = exit_cx - self.player.pos.x
            dy = exit_cy - self.player.pos.y
            angle = math.atan2(dy, dx)
            
            arrow_x = SCREEN_WIDTH // 2 + int(math.cos(angle) * 280)
            arrow_y = SCREEN_HEIGHT // 2 + int(math.sin(angle) * 180)
            arrow_x = max(30, min(SCREEN_WIDTH - 30, arrow_x))
            arrow_y = max(30, min(SCREEN_HEIGHT - 30, arrow_y))
            
            t = pygame.time.get_ticks() / 400.0
            alpha = int(150 + 100 * math.sin(t))
            
            font = pygame.font.SysFont('monospace', 11, bold=True)
            dist_m = int(math.sqrt(dx**2 + dy**2) / TILE_SIZE * 4)
            txt = font.render(f"PUERTA 7 ~{dist_m}m", True, (0, 220, 80))
            txt.set_alpha(alpha)
            self.screen.blit(txt, (arrow_x - txt.get_width()//2, arrow_y))
            
            # Flecha pequeña
            tip_x = arrow_x + int(math.cos(angle) * 14)
            tip_y = arrow_y + int(math.sin(angle) * 14)
            pygame.draw.line(self.screen, (0, 220, 80), (arrow_x, arrow_y + 14), (tip_x, tip_y + 14), 2)
    
    def _draw_pause(self):
        """Pantalla de pausa."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, 140))
        self.screen.blit(overlay, (0, 0))
        
        font = pygame.font.SysFont('monospace', 30, bold=True)
        font2 = pygame.font.SysFont('monospace', 16)
        
        txt = font.render("PAUSA", True, (200, 180, 255))
        sub = font2.render("ESC: continuar  |  R: reiniciar  |  ESC+ESC: salir", True, (180, 180, 180))
        
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 30)))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 20)))
