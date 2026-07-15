"""
Game: Clase principal del juego Sombras en la UNMSM.
Maneja el loop principal, estados del juego y coordinación de subsistemas.
Incluye soporte para Guardias y Drones de vigilancia aérea.
"""
import pygame
import sys
import math
import random
import os
from src.settings import *
from src.map_generator import ProceduralMap, total_levels
from src.tilemap import TileMap
from src.camera import Camera
from src.player import Player
from src.guard import Guard
from src.hud import HUD
from src.lighting import LightingSystem
from src.sprites import SpriteGenerator


class Stone:
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
        self.distracted = False


class CarAlarm:
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


class Drone:
    def __init__(self, x, y, patrol_points, zone, sprite_gen):
        self.pos = pygame.math.Vector2(x, y)
        self.patrol_points = patrol_points
        self.current_point_idx = 0
        self.speed = 70.0
        self.zone = zone
        self.sprite_gen = sprite_gen
        
        self.angle = 0.0
        self.animation_timer = 0.0
        self.view_angle = 75.0
        self.view_dist = 160.0
        
    def update(self, dt, player, collision_rects):
        self.animation_timer += dt * 12
        
        if not self.patrol_points:
            return False
            
        target = pygame.math.Vector2(self.patrol_points[self.current_point_idx])
        dir_vector = target - self.pos
        dist = dir_vector.length()
        
        if dist > 5:
            dir_vector.normalize_ip()
            self.pos += dir_vector * self.speed * dt
            self.angle = math.atan2(dir_vector.y, dir_vector.x)
        else:
            self.current_point_idx = (self.current_point_idx + 1) % len(self.patrol_points)
            
        if player.is_hiding:
            return False
            
        to_player = player.pos - self.pos
        player_dist = to_player.length()
        
        if player_dist <= self.view_dist:
            angle_to_player = math.atan2(to_player.y, to_player.x)
            angle_diff = math.degrees(angle_to_player - self.angle)
            angle_diff = (angle_diff + 180) % 360 - 180
            
            if abs(angle_diff) <= self.view_angle / 2:
                ray_blocked = False
                for rect in collision_rects:
                    if rect.clipline(self.pos, player.pos):
                        ray_blocked = True
                        break
                if not ray_blocked:
                    return True
                    
        return False
        
    def draw(self, screen, camera):
        sx, sy = camera.world_to_screen(int(self.pos.x), int(self.pos.y))
        
        cone_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        angle_deg = math.degrees(self.angle)
        
        p1 = self.pos
        p2 = self.pos + pygame.math.Vector2(self.view_dist, 0).rotate(angle_deg - self.view_angle / 2)
        p3 = self.pos + pygame.math.Vector2(self.view_dist, 0).rotate(angle_deg + self.view_angle / 2)
        
        sp1 = camera.world_to_screen(int(p1.x), int(p1.y))
        sp2 = camera.world_to_screen(int(p2.x), int(p2.y))
        sp3 = camera.world_to_screen(int(p3.x), int(p3.y))
        
        pygame.draw.polygon(cone_surf, (255, 0, 50, 40), [sp1, sp2, sp3])
        screen.blit(cone_surf, (0, 0))
        
        phase = int(self.animation_timer) % 4
        try:
            drone_image = self.sprite_gen.get_prop(f"drone_{phase}")
        except:
            drone_image = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(drone_image, (110, 120, 130), (16, 16), 12)
            pygame.draw.circle(drone_image, (255, 0, 0), (16, 16), 4)
            
        rotated_image = pygame.transform.rotate(drone_image, -angle_deg - 90)
        rect = rotated_image.get_rect(center=(sx, sy))
        screen.blit(rotated_image, rect.topleft)


class Game:
    """Loop principal del juego."""
    
    STATE_MENU     = 'menu'
    STATE_CONTROLS = 'controls' 
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
        
        self.sprite_gen = SpriteGenerator()
        self._init_game()
    
    def _init_game(self):
        self.current_level = 1
        self.lighting = LightingSystem(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.hud = HUD(self.screen)
        self._load_level(self.current_level, first=True)

    def _load_level(self, level_number, first=False):
        nombre_archivo = f'mapa{level_number}.tmx'
        ruta_mapa = os.path.join(BASE_DIR, 'assets', 'maps', nombre_archivo)
        
        if os.path.exists(ruta_mapa):
            self.map = TileMap(ruta_mapa, level_number)
        else:
            self.map = ProceduralMap(level_number=level_number)

        self.camera = Camera(self.map.pixel_width, self.map.pixel_height)
        spawn = self.map.spawn_point
        if first:
            self.player = Player(spawn.x, spawn.y, self.sprite_gen)
        else:
            self.player.pos = pygame.math.Vector2(spawn.x, spawn.y)
            self.player.is_hiding = False

        self.camera.offset_x = max(0, spawn.x - SCREEN_WIDTH // 2)
        self.camera.offset_y = max(0, spawn.y - SCREEN_HEIGHT // 2)

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

        self.drones = []
        if hasattr(self.map, 'drone_spawns'):
            for ddata in self.map.drone_spawns:
                drone = Drone(
                    ddata['pos'].x, ddata['pos'].y,
                    ddata['patrol'],
                    ddata['zone'],
                    self.sprite_gen
                )
                self.drones.append(drone)

        self.global_alert = 0.0
        self.stones_active = []
        self.stone_impacts = []
        self.car_alarms = []
        self.active_car_ids = set()
        self.current_zone = level_number
        self.gameover_reason = ""
        self.screen_flash = 0.0
        self.flash_color = (255, 0, 0)

        self.hud.add_notification(self.map.level_name, (255, 230, 130))
        self.hud.add_notification(self.map.level_hint, (180, 220, 255))

    def _advance_level(self):
        if self.map.is_final_level():
            self.state = self.STATE_WIN
            return
        self.current_level += 1
        self._load_level(self.current_level, first=False)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            
            self._handle_events()
            self._update(dt)
            self._draw()
        pygame.quit()
        sys.exit()
    
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # --- MANEJO DE CLICS DEL RATÓN PARA LOS MENÚS ---
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Clic Izquierdo
                    if self.state == self.STATE_MENU:
                        mouse_pos = event.pos
                        if self.hud.btn_iniciar.collidepoint(mouse_pos):
                            self.state = self.STATE_PLAYING
                        elif self.hud.btn_controles.collidepoint(mouse_pos):
                            self.state = self.STATE_CONTROLS
                        elif self.hud.btn_salir.collidepoint(mouse_pos):
                            self.running = False
                    elif self.state == self.STATE_CONTROLS:
                        self.state = self.STATE_MENU
                        
                elif event.button == 3 and self.state == self.STATE_PLAYING: # Clic Derecho
                    mouse_x, mouse_y = event.pos
                    world_x, world_y = self.camera.screen_to_world(mouse_x, mouse_y)
                    impact = self.player.throw_stone(world_x, world_y)
                    
                    if impact is not None:
                        stone = Stone(self.player.pos, impact)
                        self.stones_active.append(stone)
                        self.hud.add_notification(f"Piedra! ({self.player.stones} restantes)", (220, 200, 100))
                    elif self.player.stones <= 0:
                        self.hud.add_notification("Sin piedras!", (255, 100, 100))
                        
            # --- MANEJO DEL TECLADO ---
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == self.STATE_PLAYING:
                        self.state = self.STATE_PAUSED
                    elif self.state == self.STATE_PAUSED:
                        self.state = self.STATE_PLAYING
                    elif self.state == self.STATE_CONTROLS:
                        self.state = self.STATE_MENU
                    else:
                        self.running = False
                
                if event.key == pygame.K_RETURN and self.state == self.STATE_MENU:
                    self.state = self.STATE_PLAYING
                
                if event.key == pygame.K_r and self.state in (self.STATE_GAMEOVER, self.STATE_WIN, self.STATE_PAUSED):
                    self._init_game()
                    self.state = self.STATE_PLAYING
                
                if self.state == self.STATE_PLAYING:
                    if event.key == pygame.K_SPACE:
                        self.player.is_hiding = not self.player.is_hiding
                        if self.player.is_hiding:
                            self.hud.add_notification("Oculto!", (100, 200, 255))
                        else:
                            self.hud.add_notification("Visible", (200, 200, 100))
                    if event.key == pygame.K_q:
                        self._activate_nearest_car()
    
    def _activate_nearest_car(self):
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
            
            for guard in self.guards:
                if (guard.pos - best_car).length() <= CAR_ALARM_RADIUS:
                    guard.distract_to(best_car, CAR_ALARM_TIME)
        elif best_car:
            self.hud.add_notification("Demasiado lejos del auto", (180, 100, 100))
        else:
            self.hud.add_notification("No hay autos disponibles", (180, 100, 100))
    
    def _update(self, dt):
        if self.state != self.STATE_PLAYING:
            return
        
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        self.player.update(dt, self.map.collision_rects)
        self.camera.update(self.player.pos)
        
        self.current_zone = self.map.get_zone_at(self.player.pos.x, self.player.pos.y)
        
        seen_count = 0
        heard_count = 0
        caught = False
        
        for guard in self.guards:
            can_see, can_hear = guard.update(
                dt, self.player, self.global_alert,
                self.map.collision_rects, self.guards
            )
            if can_see:
                seen_count += 1
            if can_hear:
                heard_count += 1
            if guard.catches_player(self.player):
                caught = True
        
        drone_seen = False
        for drone in self.drones:
            if drone.update(dt, self.player, self.map.collision_rects):
                drone_seen = True
        
        if seen_count > 0 or drone_seen:
            factor_vista = seen_count + (1 if drone_seen else 0)
            self.global_alert += ALERT_RISE_SEEN * factor_vista * dt
            self.screen_flash = min(1.0, self.screen_flash + dt * 3)
            self.flash_color = (255, 0, 0)
        elif heard_count > 0:
            self.global_alert += ALERT_RISE_HEARD * dt
        else:
            self.global_alert = max(0, self.global_alert - ALERT_FALL * dt)
        
        self.global_alert = min(ALERT_MAX, self.global_alert)
        self.screen_flash = max(0, self.screen_flash - dt * 2)
        
        for stone in self.stones_active[:]:
            arrived = stone.update(dt)
            if arrived and not stone.distracted:
                stone.distracted = True
                for guard in self.guards:
                    if (guard.pos - stone.end).length() <= STONE_DISTRACT_RADIUS:
                        guard.distract_to(stone.end, STONE_DISTRACT_TIME)
                self.hud.add_notification("Guardias distraídos!", (200, 255, 100))
        
        self.stones_active = [s for s in self.stones_active if s.elapsed < 3.0]
        
        for alarm in self.car_alarms[:]:
            alarm.update(dt)
            if not alarm.active:
                self.car_alarms.remove(alarm)
        
        self.hud.update(dt, self.global_alert)
        
        if self.global_alert >= ALERT_MAX:
            self.state = self.STATE_GAMEOVER
            self.gameover_reason = "REFUERZOS LLEGARON"
            return
        if caught:
            self.state = self.STATE_GAMEOVER
            self.gameover_reason = "TE ATRAPARON"
            return
        if self.map.exit_rect and self.map.exit_rect.collidepoint(self.player.pos.x, self.player.pos.y):
            self._advance_level()
    
    def _draw(self):
        self.screen.fill(COLOR_BACKGROUND)
        if self.state == self.STATE_MENU:
            self.hud.draw_menu()
        elif self.state == self.STATE_CONTROLS:
            self.hud.draw_controls()
        elif self.state in (self.STATE_PLAYING, self.STATE_GAMEOVER, self.STATE_WIN, self.STATE_PAUSED):
            self.map.draw(self.screen, self.camera)
            self._draw_cars()
            
            for guard in self.guards:
                guard.draw(self.screen, self.camera)
            for drone in self.drones:
                drone.draw(self.screen, self.camera)
                
            self._draw_stones()
            self.player.draw(self.screen, self.camera)
            self._draw_exit_indicator()
            
            self.lighting.render_lamppost(self.screen, self.camera, self.map.lamp_positions)
            self.lighting.render(self.screen, self.camera, self.map.lamp_positions, self.player.pos, self.global_alert)
            
            if self.screen_flash > 0:
                flash_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                alpha = int(80 * self.screen_flash)
                flash_surf.fill((*self.flash_color, alpha))
                self.screen.blit(flash_surf, (0, 0))
            
            if self.state in (self.STATE_PLAYING, self.STATE_PAUSED):
                fps = self.clock.get_fps()
                self.hud.draw(self.global_alert, self.player.stones, self.current_zone, fps)
            if self.state == self.STATE_GAMEOVER:
                self.hud.draw_game_over(self.gameover_reason)
            elif self.state == self.STATE_WIN:
                self.hud.draw_win()
            elif self.state == self.STATE_PAUSED:
                self._draw_pause()
        pygame.display.flip()
    
    def _draw_cars(self):
        car_colors = [(120, 120, 140), (100, 80, 60), (60, 80, 100), (140, 90, 70), (80, 100, 80)]
        for i, car_pos in enumerate(self.map.car_positions):
            sx, sy = self.camera.world_to_screen(int(car_pos.x), int(car_pos.y))
            if not (-50 <= sx <= SCREEN_WIDTH + 50 and -50 <= sy <= SCREEN_HEIGHT + 50):
                continue
            color = car_colors[i % len(car_colors)]
            pygame.draw.ellipse(self.screen, (0, 0, 0, 80), (sx - 18, sy + 8, 36, 10))
            pygame.draw.rect(self.screen, color, (sx - 14, sy - 8, 28, 18), border_radius=3)
            pygame.draw.rect(self.screen, (50, 80, 120), (sx - 9, sy - 6, 18, 10), border_radius=2)
            
            for alarm in self.car_alarms:
                if (alarm.pos - car_pos).length() < 5:
                    if int(alarm.blink) % 2 == 0:
                        pygame.draw.rect(self.screen, (255, 150, 0), (sx - 14, sy - 8, 28, 18), 2, border_radius=3)
                        alarm_surf = pygame.Surface((CAR_ALARM_RADIUS*2, CAR_ALARM_RADIUS*2), pygame.SRCALPHA)
                        pygame.draw.circle(alarm_surf, (255, 150, 0, 20), (CAR_ALARM_RADIUS, CAR_ALARM_RADIUS), CAR_ALARM_RADIUS)
                        self.screen.blit(alarm_surf, (sx - CAR_ALARM_RADIUS, sy - CAR_ALARM_RADIUS))
    
    def _draw_stones(self):
        for stone in self.stones_active:
            sx, sy = self.camera.world_to_screen(int(stone.pos.x), int(stone.pos.y))
            pygame.draw.circle(self.screen, (160, 140, 100), (sx, sy), 4)
            pygame.draw.circle(self.screen, (190, 170, 130), (sx - 1, sy - 1), 2)
            if not stone.active:
                end_sx, end_sy = self.camera.world_to_screen(int(stone.end.x), int(stone.end.y))
                r = STONE_DISTRACT_RADIUS
                dist_surf = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
                pygame.draw.circle(dist_surf, (200, 200, 100, 30), (r, r), r)
                pygame.draw.circle(dist_surf, (200, 200, 100, 100), (r, r), r, 1)
                self.screen.blit(dist_surf, (end_sx - r, end_sy - r))
                pygame.draw.circle(self.screen, (220, 200, 120), (end_sx, end_sy), 4)
    
    def _draw_exit_indicator(self):
        if not self.map.exit_rect:
            return
        exit_rect = self.map.exit_rect
        ex, ey = self.camera.world_to_screen(exit_rect.centerx, exit_rect.centery)
        if 0 <= ex <= SCREEN_WIDTH and 0 <= ey <= SCREEN_HEIGHT:
            t = pygame.time.get_ticks() / 500.0
            glow_a = int(80 + 60 * math.sin(t))
            glow_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (0, 255, 80, glow_a), (0, 0, 60, 60), border_radius=4)
            self.screen.blit(glow_surf, (ex - 30, ey - 30))
            font = pygame.font.SysFont('monospace', 11, bold=True)
            txt = font.render("PUERTA 7", True, (0, 255, 100))
            self.screen.blit(txt, (ex - txt.get_width()//2, ey - 40))
        else:
            dx = exit_rect.centerx - self.player.pos.x
            dy = exit_rect.centery - self.player.pos.y
            angle = math.atan2(dy, dx)
            arrow_x = max(30, min(SCREEN_WIDTH - 30, SCREEN_WIDTH // 2 + int(math.cos(angle) * 280)))
            arrow_y = max(30, min(SCREEN_HEIGHT - 30, SCREEN_HEIGHT // 2 + int(math.sin(angle) * 180)))
            t = pygame.time.get_ticks() / 400.0
            alpha = int(150 + 100 * math.sin(t))
            font = pygame.font.SysFont('monospace', 11, bold=True)
            dist_m = int(math.sqrt(dx**2 + dy**2) / TILE_SIZE * 4)
            txt = font.render(f"PUERTA 7 ~{dist_m}m", True, (0, 220, 80))
            txt.set_alpha(alpha)
            self.screen.blit(txt, (arrow_x - txt.get_width()//2, arrow_y))
            tip_x = arrow_x + int(math.cos(angle) * 14)
            tip_y = arrow_y + int(math.sin(angle) * 14)
            pygame.draw.line(self.screen, (0, 220, 80), (arrow_x, arrow_y + 14), (tip_x, tip_y + 14), 2)
    
    def _draw_pause(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, 140))
        self.screen.blit(overlay, (0, 0))
        font = pygame.font.SysFont('monospace', 30, bold=True)
        font2 = pygame.font.SysFont('monospace', 16)
        txt = font.render("PAUSA", True, (200, 180, 255))
        sub = font2.render("ESC: continuar  |  R: reiniciar  |  ESC+ESC: salir", True, (180, 180, 180))
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 30)))
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 20)))