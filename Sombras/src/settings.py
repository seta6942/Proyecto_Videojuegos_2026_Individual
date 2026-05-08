"""
Configuración global del juego Sombras en la UNMSM.
"""
import os

# Pantalla
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
TITLE = "Sombras en la UNMSM"

# Tiles
TILE_SIZE = 32

# Mapa (en tiles)
MAP_WIDTH = 120   # tiles de ancho total del campus
MAP_HEIGHT = 100  # tiles de alto total del campus

# Colores principales
COLOR_BACKGROUND = (13, 0, 21)          # Negro profundo nocturno
COLOR_GROUND_DARK = (20, 35, 15)        # Verde oscuro (jardines nocturnos)
COLOR_GROUND_PATH = (45, 40, 35)        # Camino de adoquín oscuro
COLOR_GROUND_ASPHALT = (30, 30, 35)     # Asfalto
COLOR_BUILDING_MAIN = (55, 50, 65)      # Edificios color plomo/morado
COLOR_BUILDING_ACCENT = (70, 60, 80)    # Acento edificios
COLOR_GRASS = (25, 50, 20)              # Césped nocturno
COLOR_GRASS_BRIGHT = (35, 65, 28)      # Césped con luz
COLOR_STADIUM = (40, 70, 40)           # Pasto del estadio
COLOR_TRACK = (80, 60, 50)             # Pista atletismo
COLOR_WATER = (15, 30, 50)             # Agua/espejo
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (220, 30, 30)
COLOR_YELLOW = (255, 220, 0)
COLOR_ORANGE = (255, 140, 0)
COLOR_LAMPLIGHT = (255, 180, 80)       # Luz de farol
COLOR_ALERT_LOW = (0, 200, 50)
COLOR_ALERT_MED = (255, 200, 0)
COLOR_ALERT_HIGH = (255, 80, 0)

# Rutas
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
MAPS_DIR = os.path.join(ASSETS_DIR, "maps")
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
TILESETS_DIR = os.path.join(ASSETS_DIR, "tilesets")

# Jugador
PLAYER_SPEED = 3.0          # píxeles por frame normal
PLAYER_SNEAK_SPEED = 1.4    # píxeles por frame en sigilo
PLAYER_SPRINT_SPEED = 5.5   # píxeles en sprint (no silencioso)
PLAYER_SIZE = 20            # radio del jugador

# Guardias
GUARD_SPEED_PATROL = 1.4
GUARD_SPEED_ALERT = 2.0
GUARD_SPEED_CHASE = 3.2
GUARD_VISION_RANGE = 200
GUARD_VISION_ANGLE = 75     # grados de apertura del cono
GUARD_HEAR_RANGE = 120
GUARD_SIZE = 18

# Alerta Global
ALERT_RISE_SEEN = 15        # % por segundo al ser visto
ALERT_RISE_HEARD = 6        # % por segundo al ser escuchado
ALERT_FALL = 2              # % por segundo que baja
ALERT_MED_THRESHOLD = 40
ALERT_HIGH_THRESHOLD = 70
ALERT_MAX = 100

# Cámara
CAMERA_SMOOTH = 0.08        # factor de suavizado (menor = más suave)

# Iluminación nocturna
# El mapa nunca se pone totalmente negro: hay luz ambiente azulada
# para que el jugador siempre pueda ver el entorno y orientarse.
NIGHT_AMBIENT = (70, 75, 105)   # multiplicador RGB del mapa de noche (~30% brillo, tinte azul)
LAMP_RADIUS = 110               # radio de luz de farol en píxeles
PLAYER_LIGHT_RADIUS = 130       # luz que lleva el jugador (linterna)

# Zonas del campus
ZONES = {
    1: {"name": "Facultad de Matemáticas", "color": (0, 100, 150)},
    2: {"name": "Comedor y Estadio",        "color": (150, 100, 0)},
    3: {"name": "Biblioteca y Plaza Cívica","color": (0, 150, 80)},
    4: {"name": "Sistemas y Puerta 7",      "color": (150, 0, 80)},
}

# Piedras (distractores)
STONE_MAX = 3
STONE_DISTRACT_RADIUS = 100   # píxeles
STONE_DISTRACT_TIME = 4.0     # segundos

# Alarma auto
CAR_ALARM_RADIUS = 180
CAR_ALARM_TIME = 8.0
