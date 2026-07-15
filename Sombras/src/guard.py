"""
Sistema de guardias con FSM (Finite State Machine) triestado:
Patrullar -> Sospechar -> Perseguir
Cono de visión tricolor semitransparente.
"""
import pygame
import math
import random
from src.settings import *
from src.sprites import SpriteGenerator

class Guard:
    # Estados de la máquina de estados finitos (FSM)
    STATE_PATROL = 'patrol'
    STATE_SUSPECT = 'suspect'
    STATE_CHASE = 'chase'
    STATE_INVESTIGATE = 'investigate'
    
    # Paleta de colores para el cono según el estado
    CONE_COLORS = {
        STATE_PATROL:     (0,   220,  60,  60),   # Verde translúcido
        STATE_SUSPECT:    (255, 220,   0,  80),   # Amarillo
        STATE_CHASE:      (255,  30,  30, 100),   # Rojo
        STATE_INVESTIGATE:(255, 160,   0,  70),   # Naranja
    }
    
    def __init__(self, x, y, patrol_points, zone, sprite_gen, guard_id=0):
        # Posición y movimiento
        self.pos = pygame.math.Vector2(x, y)
        self.vel = pygame.math.Vector2(0, 0)
        self.patrol_points = [pygame.math.Vector2(p) for p in patrol_points]
        self.patrol_index = 0
        self.zone = zone
        self.guard_id = guard_id
        
        # Orientación y dirección visual
        self.facing_angle = 0.0   # ángulo en grados (0=derecha, 90=abajo)
        self.facing = 'down'
        
        # Estado actual y anterior de la FSM
        self.state = self.STATE_PATROL
        self.prev_state = None
        
        # Gestión de tiempos
        self.state_timer = 0.0
        self.suspect_time = 1.5    # tiempo para entrar en persecución
        self.wait_timer = 0.0
        self.investigate_timer = 0.0
        
        # Sistema de detección
        self.alert_level = 0.0     # 0-1, nivel individual de alerta
        self.last_seen_pos = None
        self.investigate_target = None
        
        # Velocidad de movimiento
        self.speed = GUARD_SPEED_PATROL
        
        # Sistema de sprites y animación
        self.sprites = sprite_gen.get_guard_sprites()
        self.anim_frame = 0
        self.anim_timer = 0.0
        self.anim_speed = 0.14
        
        # Colisión y hitbox
        self.radius = GUARD_SIZE
        self.rect = pygame.Rect(
            int(self.pos.x) - self.radius,
            int(self.pos.y) - self.radius,
            self.radius * 2,
            self.radius * 2
        )
        
        # Comportamiento aleatorio en patrulla
        self.wait_on_arrive = random.uniform(1.0, 3.0)
        
        # Parámetros sensoriales (visión y oído)
        self.vision_range = GUARD_VISION_RANGE
        self.vision_angle = GUARD_VISION_ANGLE
        self.hear_range = GUARD_HEAR_RANGE
        
        # Cache del cono de visión para optimización
        self._cone_surface = None
        self._cone_dirty = True

    def update(self, dt, player, global_alert, collision_rects, all_guards):
        """Actualiza el comportamiento y estado del guardia."""
        self.state_timer += dt
        
        # Ajuste dinámico de velocidad según alerta global
        if global_alert >= ALERT_HIGH_THRESHOLD:
            self.speed = GUARD_SPEED_CHASE * 1.1
        elif global_alert >= ALERT_MED_THRESHOLD:
            self.speed = GUARD_SPEED_ALERT
        else:
            self.speed = GUARD_SPEED_PATROL
            
        # Detección del jugador (visión y oído)
        can_see = self._can_see_player(player)
        can_hear = self._can_hear_player(player)
        
        # Máquina de estados finitos
        old_state = self.state
        
        if self.state == self.STATE_PATROL:
            self._update_patrol(dt)
            if can_see:
                self.state = self.STATE_CHASE
                self.alert_level = 1.0
                self.last_seen_pos = pygame.math.Vector2(player.pos)
            elif can_hear:
                self.state = self.STATE_SUSPECT
                self.state_timer = 0
                self.investigate_target = pygame.math.Vector2(player.pos)
                self.alert_level = 0.4
                
        elif self.state == self.STATE_SUSPECT:
            self._update_move_to(dt, self.investigate_target, collision_rects)
            if can_see:
                self.state = self.STATE_CHASE
                self.alert_level = 1.0
                self.last_seen_pos = pygame.math.Vector2(player.pos)
            elif self.state_timer > 4.0:
                self.state = self.STATE_PATROL
                self.alert_level = max(0, self.alert_level - dt * 0.3)
                self.state_timer = 0
                
        elif self.state == self.STATE_CHASE:
            self.speed = GUARD_SPEED_CHASE
            self.last_seen_pos = pygame.math.Vector2(player.pos)
            self._update_move_to(dt, player.pos, collision_rects)
            self.alert_level = 1.0
            
            if not can_see:
                # Perdió de vista: va al último lugar donde vio al jugador
                self.state = self.STATE_INVESTIGATE
                self.investigate_target = self.last_seen_pos
                self.state_timer = 0
                self.investigate_timer = 5.0
                
        elif self.state == self.STATE_INVESTIGATE:
            self._update_move_to(dt, self.investigate_target, collision_rects)
            self.investigate_timer -= dt
            self.alert_level = max(0.2, self.alert_level - dt * 0.1)
            
            if can_see:
                self.state = self.STATE_CHASE
                self.alert_level = 1.0
            elif self.investigate_timer <= 0:
                self.state = self.STATE_PATROL
                self.state_timer = 0
                self.alert_level = max(0, self.alert_level - dt * 0.2)
                
        # Actualizar cache si cambió el estado
        if old_state != self.state:
            self.state_timer = 0
            self._cone_dirty = True
            
        # Actualizar hitbox
        self.rect.x = int(self.pos.x) - self.radius
        self.rect.y = int(self.pos.y) - self.radius
        
        # Actualizar animación
        speed_len = self.vel.length()
        if speed_len > 0.1:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 4
                
        return can_see, can_hear

    def _update_patrol(self, dt):
        """Mueve al guardia a lo largo de su ruta de patrulla."""
        if not self.patrol_points:
            return
            
        target = self.patrol_points[self.patrol_index]
        direction = target - self.pos
        dist = direction.length()
        
        if dist < 8:
            # Llegó al punto: espera y luego continúa
            self.wait_timer += dt
            if self.wait_timer >= self.wait_on_arrive:
                self.wait_timer = 0
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
                self.wait_on_arrive = random.uniform(0.5, 2.0)
            self.vel = pygame.math.Vector2(0, 0)
        else:
            direction.scale_to_length(self.speed)
            self.vel = direction
            self.pos += self.vel
            self._update_facing()

    def _update_move_to(self, dt, target_pos, collision_rects):
        """Desplaza al guardia hacia una posición objetivo."""
        direction = target_pos - self.pos
        dist = direction.length()
        
        if dist > 4:
            direction.scale_to_length(self.speed)
            self.vel = direction
            new_pos = self.pos + self.vel
            
            # Detección de colisiones
            test_rect = pygame.Rect(
                new_pos.x - self.radius,
                new_pos.y - self.radius,
                self.radius * 2, self.radius * 2
            )
            collides = False
            for rect in collision_rects:
                if test_rect.colliderect(rect):
                    collides = True
                    break
                    
            if not collides:
                self.pos = new_pos
            else:
                # Intento de esquivar obstáculo
                perp = pygame.math.Vector2(-direction.y, direction.x).normalize() * self.speed
                alt_pos = self.pos + perp
                test_rect2 = pygame.Rect(
                    alt_pos.x - self.radius, alt_pos.y - self.radius,
                    self.radius * 2, self.radius * 2
                )
                col2 = any(test_rect2.colliderect(r) for r in collision_rects)
                if not col2:
                    self.pos = alt_pos
                    
            self._update_facing()
        else:
            self.vel = pygame.math.Vector2(0, 0)

    def distract_to(self, target_pos, duration):
        """Distrae al guardia hacia una posición específica (piedra/alarma)."""
        if self.state != self.STATE_CHASE:
            self.state = self.STATE_INVESTIGATE
            self.investigate_target = pygame.math.Vector2(target_pos)
            self.investigate_timer = duration
            self.state_timer = 0
            self._cone_dirty = True

    def _update_facing(self):
        """Actualiza la orientación visual según la dirección del movimiento."""
        if self.vel.length() > 0.1:
            angle = math.degrees(math.atan2(self.vel.y, self.vel.x))
            self.facing_angle = angle
            
            # Determinar dirección cardinal
            if -45 <= angle < 45:
                self.facing = 'right'
            elif 45 <= angle < 135:
                self.facing = 'down'
            elif angle >= 135 or angle < -135:
                self.facing = 'left'
            else:
                self.facing = 'up'

    def _can_see_player(self, player):
        """Detecta al jugador mediante el cono de visión."""
        if player.is_hiding:
            return False
            
        to_player = player.pos - self.pos
        dist = to_player.length()
        
        if dist > self.vision_range:
            return False
            
        # Vector de dirección del guardia
        guard_rad = math.radians(self.facing_angle)
        forward = pygame.math.Vector2(math.cos(guard_rad), math.sin(guard_rad))
        
        if dist < 1:
            return False
            
        to_player_norm = to_player / dist
        dot = forward.dot(to_player_norm)
        half_angle = math.radians(self.vision_angle / 2)
        
        return dot >= math.cos(half_angle)

    def _can_hear_player(self, player):
        """Detecta al jugador mediante el sonido."""
        if player.noise_level <= 0.05:
            return False
            
        dist = (player.pos - self.pos).length()
        effective_range = self.hear_range * player.noise_level
        return dist <= effective_range

    def draw(self, screen, camera):
        """Renderiza el cono de visión y el sprite del guardia."""
        # Verificar visibilidad en cámara
        if not camera.is_visible(self.pos.x, self.pos.y, 300):
            return
            
        sx, sy = camera.world_to_screen(int(self.pos.x), int(self.pos.y))
        
        # === CONO DE VISIÓN ===
        self._draw_vision_cone(screen, sx, sy)
        
        # === SOMBRA ===
        shadow_surf = pygame.Surface((30, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (0, 0, 30, 10))
        screen.blit(shadow_surf, (sx - 15, sy + 10))
        
        # === SPRITE DEL GUARDIA ===
        state_to_action = {
            self.STATE_PATROL: 'patrol',
            self.STATE_SUSPECT: 'suspect',
            self.STATE_CHASE: 'chase',
            self.STATE_INVESTIGATE: 'distracted'
        }
        action = state_to_action.get(self.state, 'patrol')
        
        sprite_key = f"{self.facing}_{action}"
        
        # Fallback a patrol si no encuentra los frames
        frames = self.sprites.get(sprite_key, self.sprites.get(f"{self.facing}_patrol", []))
        
        if frames:
            frame_idx = self.anim_frame % len(frames)
            sprite = frames[frame_idx]
            sprite_rect = sprite.get_rect(center=(sx, sy))
            screen.blit(sprite, sprite_rect)
            
        # === INDICADORES DE ESTADO ===
        if self.state == self.STATE_SUSPECT:
            # Signo de interrogación amarillo
            font_small = pygame.font.SysFont('monospace', 18, bold=True)
            txt = font_small.render('?', True, (255, 220, 0))
            screen.blit(txt, (sx - 5, sy - 36))
        elif self.state == self.STATE_CHASE:
            # Signo de exclamación rojo
            font_small = pygame.font.SysFont('monospace', 18, bold=True)
            txt = font_small.render('!', True, (255, 30, 30))
            screen.blit(txt, (sx - 4, sy - 36))

    def _draw_vision_cone(self, screen, sx, sy):
        """Dibuja el cono de visión semitransparente."""
        color = self.CONE_COLORS.get(self.state, (0, 255, 0, 60))
        
        cone_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Calcular ángulos del cono
        base_angle = self.facing_angle
        half = self.vision_angle / 2
        
        # Rango visual adaptado al estado
        vis_range = self.vision_range
        if self.state == self.STATE_CHASE:
            vis_range *= 1.3
            
        # Generar polígono del cono
        segments = 20
        points = [(sx, sy)]
        for i in range(segments + 1):
            t = i / segments
            angle_deg = base_angle - half + t * self.vision_angle
            angle_rad = math.radians(angle_deg)
            px = sx + math.cos(angle_rad) * vis_range
            py = sy + math.sin(angle_rad) * vis_range
            points.append((px, py))
            
        if len(points) >= 3:
            pygame.draw.polygon(cone_surf, color, points)
            
        screen.blit(cone_surf, (0, 0))

    def get_world_rect(self):
        """Retorna el rectángulo de colisión en coordenadas del mundo."""
        return pygame.Rect(
            int(self.pos.x) - self.radius,
            int(self.pos.y) - self.radius,
            self.radius * 2,
            self.radius * 2
        )

    def catches_player(self, player):
        """Determina si el guardia atrapa al jugador (distancia < 20px)."""
        dist = (self.pos - player.pos).length()
        return dist < 20 and self.state == self.STATE_CHASE