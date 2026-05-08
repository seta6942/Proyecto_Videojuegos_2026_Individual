"""
Sistema de cámara con seguimiento suave del jugador.
"""
import pygame
from src.settings import *


class Camera:
    def __init__(self, map_width, map_height):
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.map_width = map_width
        self.map_height = map_height
    
    def update(self, target_pos):
        """Actualiza la cámara para seguir al objetivo con suavizado."""
        target_x = target_pos.x - SCREEN_WIDTH // 2
        target_y = target_pos.y - SCREEN_HEIGHT // 2
        
        # Clamp para no salir del mapa
        target_x = max(0, min(target_x, self.map_width - SCREEN_WIDTH))
        target_y = max(0, min(target_y, self.map_height - SCREEN_HEIGHT))
        
        # Interpolación suave (lerp)
        self.offset_x += (target_x - self.offset_x) * CAMERA_SMOOTH * 4
        self.offset_y += (target_y - self.offset_y) * CAMERA_SMOOTH * 4
        
        # Clamp final
        self.offset_x = max(0, min(self.offset_x, self.map_width - SCREEN_WIDTH))
        self.offset_y = max(0, min(self.offset_y, self.map_height - SCREEN_HEIGHT))
    
    def get_offset(self):
        """Retorna el offset como tupla para blit."""
        return (-int(self.offset_x), -int(self.offset_y))
    
    def world_to_screen(self, world_x, world_y):
        """Convierte coordenadas del mundo a coordenadas de pantalla."""
        return (
            int(world_x - self.offset_x),
            int(world_y - self.offset_y)
        )
    
    def screen_to_world(self, screen_x, screen_y):
        """Convierte coordenadas de pantalla a coordenadas del mundo."""
        return (
            screen_x + self.offset_x,
            screen_y + self.offset_y
        )
    
    def apply_to_rect(self, rect):
        """Aplica el offset de cámara a un rect."""
        return pygame.Rect(
            rect.x - int(self.offset_x),
            rect.y - int(self.offset_y),
            rect.width,
            rect.height
        )
    
    def is_visible(self, world_x, world_y, margin=64):
        """Verifica si un punto del mundo es visible en pantalla."""
        sx, sy = self.world_to_screen(world_x, world_y)
        return (
            -margin <= sx <= SCREEN_WIDTH + margin and
            -margin <= sy <= SCREEN_HEIGHT + margin
        )
