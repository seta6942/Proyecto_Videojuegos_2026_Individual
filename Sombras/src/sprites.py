"""
Generador de sprites programáticos y cargador de assets para el juego.
"""
import pygame
import os
from src.settings import *

class SpriteGenerator:
    """Genera sprites pixel art para tiles y carga assets de personajes y props."""
    
    def __init__(self):
        pygame.font.init()
        self._player_sprites = None
        self._guard_sprites = None
        self._drone_sprites = None
        self._tile_sprites = {}
        
        # Ruta base de sprites desde settings
        self.sprites_dir = SPRITES_DIR

    # --- CARGA DE SPRITES DE PERSONAJES ---

    def get_player_sprites(self):
        """Retorna los sprites del jugador."""
        if self._player_sprites is None:
            self._player_sprites = self._load_character_sprites('player')
        return self._player_sprites

    def get_guard_sprites(self):
        """Retorna los sprites de los guardias."""
        if self._guard_sprites is None:
            self._guard_sprites = self._load_character_sprites('guard')
        return self._guard_sprites

    def _load_character_sprites(self, character_folder):
        """Carga frames desde assets/sprites/<character_folder>/."""
        sprites = {}
        directions = ['down', 'up', 'left', 'right']
        char_path = os.path.join(self.sprites_dir, character_folder)
        
        # JUGADOR: Formato down_0.png y down_sneak_0.png
        if character_folder == 'player':
            for facing in directions:
                frames = []
                sneak_frames = []
                
                for phase in range(4):
                    normal_file = os.path.join(char_path, f"{facing}_{phase}.png")
                    normal_img = self._load_image_or_fallback(normal_file)
                    frames.append(normal_img)
                    
                    sneak_file = os.path.join(char_path, f"{facing}_sneak_{phase}.png")
                    if os.path.exists(sneak_file):
                        sneak_frames.append(self._load_image_or_fallback(sneak_file))
                    else:
                        # Fallback: encoger la imagen normal
                        w, h = normal_img.get_size()
                        sneak_img = pygame.transform.scale(normal_img, (w, int(h * 0.75)))
                        sneak_surf = pygame.Surface((w, h), pygame.SRCALPHA)
                        sneak_surf.blit(sneak_img, (0, h - int(h * 0.75)))
                        sneak_frames.append(sneak_surf)

                sprites[facing] = frames
                sprites[f"{facing}_sneak"] = sneak_frames
                sprites[f"{facing}_sprint"] = frames  # Sprint usa frames normales

        # GUARDIA: Formato down_0_patrol.png, down_0_chase.png, etc.
        elif character_folder == 'guard':
            actions = ['patrol', 'suspect', 'chase', 'distracted']
            for facing in directions:
                for action in actions:
                    action_frames = []
                    for phase in range(4):
                        action_file = os.path.join(char_path, f"{facing}_{phase}_{action}.png")
                        action_frames.append(self._load_image_or_fallback(action_file))
                    sprites[f"{facing}_{action}"] = action_frames

        return sprites

    # --- CARGA DE PROPS Y OBJETOS ---

    def get_drone_sprites(self):
        """Carga la animación del dron (drone_0.png, drone_1.png)."""
        if self._drone_sprites is None:
            self._drone_sprites = []
            prop_path = os.path.join(self.sprites_dir, 'props')
            for phase in range(2):  # drone_0.png y drone_1.png
                filepath = os.path.join(prop_path, f"drone_{phase}.png")
                self._drone_sprites.append(self._load_image_or_fallback(filepath))
        return self._drone_sprites

    def get_prop(self, prop_name):
        """Carga objetos estáticos como 'stone', 'camera_active', etc."""
        filepath = os.path.join(self.sprites_dir, 'props', f"{prop_name}.png")
        return self._load_image_or_fallback(filepath)

    def _load_image_or_fallback(self, filepath, size=(32, 32)):
        """Carga una imagen o devuelve un cuadro morado de respaldo."""
        if os.path.exists(filepath):
            try:
                img = pygame.image.load(filepath).convert_alpha()
                return pygame.transform.scale(img, size)
            except pygame.error:
                pass
        
        # Fallback: cuadrado morado con borde blanco
        fallback = pygame.Surface(size, pygame.SRCALPHA)
        fallback.fill((150, 0, 150, 180))
        pygame.draw.rect(fallback, (255, 255, 255), fallback.get_rect(), 2)
        return fallback

    # =========================================================================
    # GENERACIÓN DE TILES DEL MAPA
    # =========================================================================

    def get_tile(self, tile_type):
        """Retorna un tile pixel art para el tipo especificado."""
        if tile_type in self._tile_sprites:
            return self._tile_sprites[tile_type]
            
        tile = self._create_tile(tile_type)
        self._tile_sprites[tile_type] = tile
        return tile
        
    def _create_tile(self, tile_type):
        """Crea un tile de 32x32 píxeles para el tipo indicado."""
        size = 32
        surf = pygame.Surface((size, size))
        
        if tile_type == 'grass':
            surf.fill((25, 50, 20))
            import random
            random.seed(hash(tile_type))
            for _ in range(8):
                x = random.randint(2, 29)
                y = random.randint(2, 29)
                pygame.draw.line(surf, (35, 65, 28), (x, y), (x, y-3), 1)
                
        elif tile_type == 'path':
            surf.fill((55, 48, 40))
            pygame.draw.rect(surf, (65, 58, 50), (1, 1, 30, 30))
            # Textura de adoquín
            for gy in range(0, 32, 8):
                pygame.draw.line(surf, (40, 35, 28), (0, gy), (32, gy), 1)
            for gx in range(0, 32, 8):
                pygame.draw.line(surf, (40, 35, 28), (gx, 0), (gx, 32), 1)
                
        elif tile_type == 'asphalt':
            surf.fill((35, 35, 40))
            import random
            random.seed(42)
            for _ in range(5):
                x = random.randint(0, 31)
                y = random.randint(0, 31)
                pygame.draw.circle(surf, (40, 40, 45), (x, y), 1)
                
        elif tile_type == 'building_floor':
            surf.fill((60, 55, 70))
            pygame.draw.rect(surf, (50, 45, 60), (0, 0, 32, 1))
            pygame.draw.rect(surf, (50, 45, 60), (0, 0, 1, 32))
            
        elif tile_type == 'building_wall':
            surf.fill((70, 60, 80))
            # Textura de ladrillos
            for gy in range(0, 32, 8):
                offset_x = (gy // 8 % 2) * 4
                for gx in range(-offset_x, 32, 8):
                    pygame.draw.rect(surf, (80, 70, 90), (gx+1, gy+1, 6, 6))
                    pygame.draw.rect(surf, (55, 45, 65), (gx, gy, 8, 8), 1)
                    
        elif tile_type == 'water':
            surf.fill((15, 30, 55))
            for i in range(3):
                y = 6 + i * 10
                pygame.draw.line(surf, (25, 50, 80), (2, y), (28, y), 1)
                pygame.draw.line(surf, (20, 40, 70), (4, y+2), (25, y+2), 1)
                
        elif tile_type == 'stadium_grass':
            surf.fill((35, 70, 35))
            # Líneas del campo de fútbol
            for i in range(0, 32, 6):
                alpha = 255 if (i // 6 % 2 == 0) else 180
                color = (45, 90, 45) if (i // 6 % 2 == 0) else (30, 60, 30)
                pygame.draw.rect(surf, color, (i, 0, 6, 32))
                
        elif tile_type == 'track':
            surf.fill((80, 60, 45))
            pygame.draw.rect(surf, (90, 70, 55), (1, 1, 30, 30))
            
        elif tile_type == 'lamp_base':
            surf.fill((25, 50, 20))
            pygame.draw.circle(surf, (90, 90, 90), (16, 16), 3)
            pygame.draw.line(surf, (80, 80, 80), (16, 16), (16, 4), 2)
            
        elif tile_type == 'tree':
            surf.fill((25, 50, 20))
            # Tronco
            pygame.draw.rect(surf, (60, 40, 20), (13, 18, 6, 10))
            # Copa del árbol
            pygame.draw.circle(surf, (20, 80, 20), (16, 14), 12)
            pygame.draw.circle(surf, (30, 100, 30), (13, 12), 7)
            pygame.draw.circle(surf, (15, 65, 15), (20, 15), 6)
            
        elif tile_type == 'fence':
            surf.fill((0, 0, 0, 0))
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.rect(surf, (80, 70, 60), (0, 14, 32, 4))
            for fx in range(0, 32, 6):
                pygame.draw.rect(surf, (80, 70, 60), (fx, 8, 3, 18))
                
        elif tile_type == 'concrete_wall':
            # Muro perimetral de concreto
            surf.fill((100, 100, 105))
            pygame.draw.rect(surf, (75, 75, 80), (0, 0, 32, 32), 2)
            pygame.draw.line(surf, (60, 60, 65), (0, 16), (32, 16), 1)
            pygame.draw.line(surf, (60, 60, 65), (16, 0), (16, 32), 1)
            
        elif tile_type == 'bush':
            # Arbusto cuadrado denso para cobertura
            surf.fill((25, 50, 20))
            pygame.draw.rect(surf, (20, 65, 25), (3, 3, 26, 26))
            pygame.draw.rect(surf, (15, 55, 18), (3, 3, 26, 26), 2)
            for px in (8, 16, 24):
                for py in (8, 16, 24):
                    pygame.draw.circle(surf, (30, 80, 30), (px, py), 2)
                    
        elif tile_type == 'gate':
            # Portón Puerta 7 (dorado, entreabierto)
            surf.fill((25, 25, 30))
            pygame.draw.rect(surf, (160, 130, 60), (0, 6, 32, 4))
            pygame.draw.rect(surf, (160, 130, 60), (0, 22, 32, 4))
            for fx in range(2, 32, 8):
                pygame.draw.rect(surf, (180, 150, 70), (fx, 6, 2, 20))
            # Brillo dorado
            pygame.draw.circle(surf, (255, 220, 120), (16, 16), 3)
            
        elif tile_type == 'camera_panel':
            # Panel de cámara con luz roja
            surf.fill((45, 45, 50))
            pygame.draw.rect(surf, (60, 60, 65), (4, 4, 24, 24))
            pygame.draw.rect(surf, (30, 30, 35), (4, 4, 24, 24), 2)
            pygame.draw.circle(surf, (15, 15, 18), (16, 16), 6)
            pygame.draw.circle(surf, (255, 30, 30), (16, 16), 3)
            pygame.draw.circle(surf, (255, 150, 150), (15, 15), 1)
            
        elif tile_type == 'statue':
            # Estatua de piedra sobre base
            surf.fill((55, 48, 40))
            pygame.draw.rect(surf, (140, 130, 120), (8, 8, 16, 16))
            pygame.draw.rect(surf, (90, 85, 80), (8, 8, 16, 16), 2)
            pygame.draw.rect(surf, (170, 160, 150), (12, 4, 8, 12))
            pygame.draw.circle(surf, (180, 170, 160), (16, 6), 3)
            
        elif tile_type == 'parking_line':
            # Asfalto con línea de estacionamiento
            surf.fill((35, 35, 40))
            pygame.draw.line(surf, (200, 200, 200), (0, 28), (32, 4), 2)
            
        elif tile_type == 'roof':
            # Techo plano de edificio
            surf.fill((85, 75, 95))
            pygame.draw.rect(surf, (65, 55, 75), (0, 0, 32, 32), 1)
            pygame.draw.line(surf, (105, 95, 115), (0, 8), (32, 8), 1)
            pygame.draw.line(surf, (105, 95, 115), (0, 24), (32, 24), 1)
            
        else:  # Tile por defecto
            surf.fill((20, 35, 15))
            
        return surf