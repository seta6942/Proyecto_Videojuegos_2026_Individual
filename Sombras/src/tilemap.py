"""
Sistema de carga y renderizado del mapa TMX.
Usa pytmx para cargar el campus UNMSM de manera dinámica por niveles.
"""
import pygame
import pytmx
import os
from src.settings import *


class TileMap:
    def __init__(self, filename, level_number):
        # Carga el archivo TMX utilizando la librería pytmx
        self.tmx_data = pytmx.load_pygame(filename, pixelalpha=True)
        self.width = self.tmx_data.width * self.tmx_data.tilewidth
        self.height = self.tmx_data.height * self.tmx_data.tileheight
        self.tilewidth = self.tmx_data.tilewidth
        self.tileheight = self.tmx_data.tileheight
        self.level_number = level_number
        
        # Atributos de compatibilidad requeridos por la cámara en game.py
        self.pixel_width = self.width
        self.pixel_height = self.height
        
        # Configuración dinámica de nombres de nivel y pistas
        nombres_niveles = {
            1: "Facultad de Ciencias Matemáticas",
            2: "Zona de Control 2: Comedor Universitario / Estadio",
            3: "Zona de Control 3: Plaza Cívica (Rectorado)",
            4: "Zona de Control 4: Fac. de Ingeniería de Sistemas / Puerta 7"
        }
        hints_niveles = {
            1: "Tutorial: Esquiva los conos de visión roja de las patrullas usando las sombras.",
            2: "Estacionamiento: Usa las alarmas de los autos ('Q') para distraer a los guardias.",
            3: "Plaza Central: Lanza piedras con Clic Derecho para crear ruido alejado de tu posición.",
            4: "¡Escape Final! Encuentra la reja perimetral de la Puerta 7 entreabierta para ganar."
        }
        
        self.level_name = nombres_niveles.get(level_number, f"Zona Universitaria {level_number}")
        self.level_hint = hints_niveles.get(level_number, "Muévete con sigilo y vigila las rutas de las patrullas.")
        
        self.collision_rects = []
        self.lamp_positions = []
        self.spawn_point = pygame.math.Vector2(80, 700)
        self.exit_rect = pygame.Rect(0, 0, 32, 32)
        self.car_positions = []
        self.stone_positions = []
        self.guard_spawns = []
        self.drone_spawns = []  
        
        # Cargar primero las colisiones para el correcto funcionamiento del radar
        self._load_collision_layer()
        self._load_objects()
        
        # Pre-renderizar el mapa
        self.surface = self._render_map()
    
    def _calculate_smart_patrol(self, start_x, start_y):
        """Calcula una ruta inteligente para la patrulla evitando paredes."""
        ts = self.tilewidth
        max_tiles = 5
        
        espacio_derecha = 0
        for i in range(1, max_tiles + 1):
            check_x = start_x + (i * ts)
            check_rect = pygame.Rect(check_x, start_y, ts, ts)
            if any(rect.colliderect(check_rect) for rect in self.collision_rects):
                break
            espacio_derecha += 1
            
        if espacio_derecha >= 2:
            return [(start_x, start_y), (start_x + (espacio_derecha * ts), start_y)]
            
        espacio_abajo = 0
        for i in range(1, max_tiles + 1):
            check_y = start_y + (i * ts)
            check_rect = pygame.Rect(start_x, check_y, ts, ts)
            if any(rect.colliderect(check_rect) for rect in self.collision_rects):
                break
            espacio_abajo += 1
            
        if espacio_abajo >= 2:
            return [(start_x, start_y), (start_x, start_y + (espacio_abajo * ts))]
            
        return [(start_x, start_y), (start_x + ts, start_y)]

    def _load_collision_layer(self):
        """Filtra y extrae los rectángulos de colisión tolerando mayúsculas y acentos."""
        nombres_validos = ['collision', 'colision', 'colisión']
        for layer in self.tmx_data.layers:
            if hasattr(layer, 'name'):
                if layer.name.lower() in nombres_validos:
                    for x, y, gid in layer:
                        if gid:
                            rect = pygame.Rect(
                                x * self.tilewidth,
                                y * self.tileheight,
                                self.tilewidth,
                                self.tileheight
                            )
                            self.collision_rects.append(rect)

    def _load_objects(self):
        """Procesa los puntos lógicos de spawn creados en Tiled."""
        if hasattr(self.tmx_data, 'objectgroups'):
            for og in self.tmx_data.objectgroups:
                for obj in og:
                    name = getattr(obj, 'name', '') or ''
                    type_ = getattr(obj, 'type', '') or ''
                    props = obj.properties if hasattr(obj, 'properties') else {}
                    
                    if name == 'spawn' or type_ == 'spawn':
                        self.spawn_point = pygame.math.Vector2(obj.x, obj.y)
                    elif name == 'exit' or type_ == 'exit':
                        self.exit_rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)
                    elif name == 'lamp' or type_ == 'lamp':
                        self.lamp_positions.append((obj.x, obj.y))
                    elif name == 'car' or type_ == 'car':
                        self.car_positions.append(pygame.math.Vector2(obj.x, obj.y))
                    elif name == 'stone' or type_ == 'stone':
                        self.stone_positions.append(pygame.math.Vector2(obj.x, obj.y))
                    elif name == 'guard_spawn' or type_ == 'guard_spawn':
                        ruta_dinamica = self._calculate_smart_patrol(obj.x, obj.y)
                        self.guard_spawns.append({
                            'pos': pygame.math.Vector2(obj.x, obj.y),
                            'zone': props.get('zone', self.level_number),
                            'patrol': ruta_dinamica
                        })
                    elif name == 'drone_spawn' or type_ == 'drone_spawn':
                        ruta_dinamica = self._calculate_smart_patrol(obj.x, obj.y)
                        self.drone_spawns.append({
                            'pos': pygame.math.Vector2(obj.x, obj.y),
                            'zone': props.get('zone', self.level_number),
                            'patrol': ruta_dinamica
                        })
    
    def _render_map(self):
        """Pinta ABSOLUTAMENTE TODAS las capas visibles, incluyendo tus paredes."""
        surface = pygame.Surface((self.width, self.height))
        surface.fill(COLOR_BACKGROUND)
        
        for layer in self.tmx_data.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                for x, y, gid in layer:
                    if gid:
                        tile = self.tmx_data.get_tile_image_by_gid(gid)
                        if tile:
                            surface.blit(tile, (x * self.tilewidth, y * self.tileheight))
        return surface
    
    def draw(self, screen, camera):
        offset = camera.get_offset()
        screen.blit(self.surface, offset)
    
    def get_collision_rects(self):
        return self.collision_rects
    
    def get_zone_at(self, world_x, world_y):
        return self.level_number
        
    def is_final_level(self):
        return self.level_number == 4

    def is_solid(self, world_x, world_y):
        for rect in self.collision_rects:
            if rect.collidepoint(world_x, world_y):
                return True
        return False
#SETA
