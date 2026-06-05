"""
Jugador: Melvin, estudiante de Computación Científica de la UNMSM.
Sprite top-down con manejo de sigilo, sprint y físicas.
"""
import pygame
import math
from src.settings import *
from src.sprites import SpriteGenerator

class Player:
    def __init__(self, x, y, sprite_gen):
        self.pos = pygame.math.Vector2(x, y)
        self.vel = pygame.math.Vector2(0, 0)
        self.direction = 0  # Ángulo en grados (0=arriba, 90=derecha, y respectivamnte "referencia")
        self.facing = 'down'  
        
        self.state = 'idle'      
        self.is_sneaking = False
        self.is_hiding = False
        self.is_sprinting = False
        
        self.speed = PLAYER_SPEED
        
        # Stones inventory
        self.stones = STONE_MAX
        self.stone_throw_cooldown = 0
        
        # Animación
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_speed = 0.12  # segundos por frame
        self.walk_frames = 4
        
        # Sprites
        self.sprites = sprite_gen.get_player_sprites()
        self.current_sprite = self.sprites['down'][0]
        
        # Hitbox
        self.radius = PLAYER_SIZE
        self.rect = pygame.Rect(
            int(self.pos.x) - self.radius,
            int(self.pos.y) - self.radius,
            self.radius * 2,
            self.radius * 2
        )
        
        # Estado de visibilidad/detección
        self.is_visible_to_guard = False
        self.noise_level = 0.0   # 0=silencioso, 1=máximo ruido
        
        # Efectos
        self.hide_timer = 0
        self.footstep_timer = 0

    def handle_input(self, keys):
        dx, dy = 0, 0
        
        # WASD / Flechas
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -1
            self.facing = 'up'
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = 1
            self.facing = 'down'
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx = -1
            self.facing = 'left'
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx = 1
            self.facing = 'right'
            
        # Diagonal normalizada
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707
            
        # Shift = sigilo
        self.is_sneaking = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        # Ctrl = sprint (ruidoso)
        self.is_sprinting = (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]) and not self.is_sneaking
        
        # Velocidad según estado
        if self.is_sneaking:
            speed = PLAYER_SNEAK_SPEED
            self.state = 'sneak'
            self.noise_level = 0.0
        elif self.is_sprinting:
            speed = PLAYER_SPRINT_SPEED
            self.state = 'sprint'
            self.noise_level = 1.0
        else:
            speed = PLAYER_SPEED
            self.state = 'walk' if (dx != 0 or dy != 0) else 'idle'
            self.noise_level = 0.4 if (dx != 0 or dy != 0) else 0.0
            
        if dx == 0 and dy == 0:
            self.noise_level = 0.0
            
        self.vel.x = dx * speed
        self.vel.y = dy * speed

    def update(self, dt, collision_rects):
        # Movimiento con colisión
        new_pos = self.pos + self.vel
        
        # Check colisiones X
        test_rect_x = pygame.Rect(
            new_pos.x - self.radius,
            self.pos.y - self.radius,
            self.radius * 2, self.radius * 2
        )
        col_x = False
        for rect in collision_rects:
            if test_rect_x.colliderect(rect):
                col_x = True
                break
                
        if not col_x:
            self.pos.x = new_pos.x
            
        # Check colisiones Y
        test_rect_y = pygame.Rect(
            self.pos.x - self.radius,
            new_pos.y - self.radius,
            self.radius * 2, self.radius * 2
        )
        col_y = False
        for rect in collision_rects:
            if test_rect_y.colliderect(rect):
                col_y = True
                break
                
        if not col_y:
            self.pos.y = new_pos.y
            
        # Actualizar rect
        self.rect.x = int(self.pos.x) - self.radius
        self.rect.y = int(self.pos.y) - self.radius
        
        # Animación
        if self.vel.length() > 0.1:
            self.anim_timer += dt
            if self.anim_timer >= self.anim_speed:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % self.walk_frames
        else:
            self.anim_frame = 0
            self.anim_timer = 0
            
        # Actualizar sprite
        if self.is_sneaking:
            key = self.facing + '_sneak'
        elif self.is_sprinting:
            key = self.facing + '_sprint'
        else:
            key = self.facing
            
        frames = self.sprites.get(key, self.sprites.get(self.facing, [self.current_sprite]))
        frame_idx = self.anim_frame % len(frames)
        self.current_sprite = frames[frame_idx]
        
        # Cooldown piedra
        if self.stone_throw_cooldown > 0:
            self.stone_throw_cooldown -= dt

    def throw_stone(self, world_target_x, world_target_y):
        """Lanza una piedra hacia el punto dado. Retorna la posición de impacto si tiene piedras."""
        if self.stones <= 0 or self.stone_throw_cooldown > 0:
            return None
            
        self.stones -= 1
        self.stone_throw_cooldown = 0.5
        
        # Calcular dirección
        dx = world_target_x - self.pos.x
        dy = world_target_y - self.pos.y
        dist = math.sqrt(dx*dx + dy*dy)
        
        # Limitar distancia máxima de lanzamiento
        max_range = 250
        if dist > max_range:
            ratio = max_range / dist
            dx *= ratio
            dy *= ratio
            
        impact_x = self.pos.x + dx
        impact_y = self.pos.y + dy
        
        return pygame.math.Vector2(impact_x, impact_y)

    def draw(self, screen, camera):
        sx, sy = camera.world_to_screen(int(self.pos.x), int(self.pos.y))
        
        # Dibujar sombra
        if not self.is_hiding:
            shadow_surf = pygame.Surface((28, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (0, 0, 28, 10))
            screen.blit(shadow_surf, (sx - 14, sy + 10))
            
        # Dibujar sprite centrado
        sprite_rect = self.current_sprite.get_rect(center=(sx, sy))
        
        if self.is_hiding:
            # Mostrar semitransparente si está oculto
            temp = self.current_sprite.copy()
            temp.set_alpha(120)
            screen.blit(temp, sprite_rect)
        else:
            screen.blit(self.current_sprite, sprite_rect)
            
        # Indicador de sigilo
        if self.is_sneaking:
            pygame.draw.circle(screen, (0, 200, 255, 100), (sx, sy - 20), 5)

    def get_world_rect(self):
        return pygame.Rect(
            int(self.pos.x) - self.radius,
            int(self.pos.y) - self.radius,
            self.radius * 2,
            self.radius * 2
        )
