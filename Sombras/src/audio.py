"""
Motor de Audio para sonidos y música dinámica.
"""
import pygame
import os
from src.settings import BASE_DIR, ALERT_MAX

class AudioEngine:
    def __init__(self):
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False
        
        self.sounds = {}
        self.music_playing = False
        self.audio_dir = os.path.join(BASE_DIR, 'assets', 'audio')
        
        if not os.path.exists(self.audio_dir):
            try:
                os.makedirs(self.audio_dir)
            except:
                pass

        self._init_sounds()
        
    def _init_sounds(self):
        if not self.enabled: return
        
        # Diccionario con los nombres de archivo esperados
        sound_files = {
            'step_grass': 'step_grass.wav',
            'step_path': 'step_path.wav',
            'step_asphalt': 'step_asphalt.wav',
            'car_alarm': 'car_alarm.wav',
            'stone_impact': 'stone_impact.wav'
        }
        
        for name, filename in sound_files.items():
            path = os.path.join(self.audio_dir, filename)
            if os.path.exists(path):
                self.sounds[name] = pygame.mixer.Sound(path)
            else:
                self.sounds[name] = None
                
        # Archivo de música BGM para la tensión
        self.music_file = os.path.join(self.audio_dir, 'tension_bgm.ogg')

    def play_sound(self, name, volume=1.0):
        if not self.enabled: return
        if name in self.sounds and self.sounds[name]:
            self.sounds[name].set_volume(volume)
            self.sounds[name].play()

    def update_tension_music(self, global_alert):
        if not self.enabled: return
        
        # Iniciar la música si no está sonando
        if not self.music_playing:
            if os.path.exists(self.music_file):
                try:
                    pygame.mixer.music.load(self.music_file)
                    pygame.mixer.music.play(-1)
                    self.music_playing = True
                except pygame.error:
                    pass
        
        # Actualizar el volumen basado en el nivel de alerta
        if self.music_playing:
            base_vol = 0.2  # Volumen mínimo de tensión
            alert_factor = (global_alert / ALERT_MAX) * 0.6
            pygame.mixer.music.set_volume(base_vol + alert_factor)