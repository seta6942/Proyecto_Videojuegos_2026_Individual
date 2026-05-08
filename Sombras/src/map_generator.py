"""
Generador de NIVELES del campus UNMSM.
Cada nivel es UN PEDAZO ESPECÍFICO del campus, modelado con detalle
para que sea reconocible como UNMSM.

Tile glyphs:
  '0' grass (jardín)        '1' camino adoquín          '2' asfalto
  '3' pared edificio        '4' piso edificio           '5' césped estadio
  '6' pista atletismo       '7' agua / fuente           '8' árbol
  'W' muro perimetral SOLID 'B' arbusto SOLID (cover)   'C' cámara SOLID
  'S' estatua SOLID         'G' portón Puerta 7         'P' asfalto+línea
  'R' techo elevado SOLID   'X' vacío fuera del nivel   'E' salida
"""
import math
import pygame
from src.settings import TILE_SIZE, COLOR_BACKGROUND
from src.sprites import SpriteGenerator


# ================ HELPERS ================

class _SimpleRNG:
    def __init__(self, seed):
        self.state = (seed * 1103515245 + 12345) & 0x7fffffff
    def next(self):
        self.state = (self.state * 1103515245 + 12345) & 0x7fffffff
        return self.state


def _set(tiles, x, y, ch):
    H = len(tiles); W = len(tiles[0])
    if 0 <= x < W and 0 <= y < H:
        tiles[y][x] = ch


def _fill_area(tiles, x, y, w, h, tile, only_on=None):
    H = len(tiles); W = len(tiles[0])
    for dy in range(h):
        for dx in range(w):
            tx, ty = x + dx, y + dy
            if 0 <= tx < W and 0 <= ty < H:
                if only_on is None or tiles[ty][tx] in only_on:
                    tiles[ty][tx] = tile


def _place_building(tiles, x, y, w, h, fill='4', wall='3'):
    """Edificio rectangular sólido."""
    H = len(tiles); W = len(tiles[0])
    for dy in range(h):
        for dx in range(w):
            tx, ty = x + dx, y + dy
            if 0 <= tx < W and 0 <= ty < H:
                if dx == 0 or dx == w-1 or dy == 0 or dy == h-1:
                    tiles[ty][tx] = wall
                else:
                    tiles[ty][tx] = fill


def _place_stepped_building(tiles, x, y, sections):
    """Edificio escalonado tipo Matemáticas: lista de [(dx, dy, w, h)]."""
    for dx, dy, w, h in sections:
        _place_building(tiles, x+dx, y+dy, w, h)


def _place_u_building(tiles, x, y, w, h, opening_w, opening_dir='S'):
    """Edificio en U/C con la abertura en una dirección."""
    _place_building(tiles, x, y, w, h)
    ow = max(3, opening_w)
    ox = x + (w - ow)//2
    if opening_dir == 'S':  # abertura hacia el sur
        for dy in range(h//2, h):
            for dx in range(ow):
                _set(tiles, ox+dx, y+dy, '1')
    elif opening_dir == 'N':
        for dy in range(0, h//2):
            for dx in range(ow):
                _set(tiles, ox+dx, y+dy, '1')
    elif opening_dir == 'E':
        oy = y + (h - ow)//2
        for dx in range(w//2, w):
            for dy in range(ow):
                _set(tiles, x+dx, oy+dy, '1')


def _place_t_building(tiles, cx, cy, arm_len=8, arm_thick=5, stem_len=10, stem_thick=6, dir='S'):
    """Edificio en T o cruz: arm horizontal centrado en (cx,cy), stem hacia 'dir'."""
    # Brazo horizontal
    _place_building(tiles, cx - arm_len, cy - arm_thick//2, arm_len*2, arm_thick)
    # Stem
    if dir == 'S':
        _place_building(tiles, cx - stem_thick//2, cy + arm_thick//2, stem_thick, stem_len)
    elif dir == 'N':
        _place_building(tiles, cx - stem_thick//2, cy - arm_thick//2 - stem_len, stem_thick, stem_len)


def _place_circle_plaza(tiles, cx, cy, r, tile='1'):
    """Plaza adoquinada circular."""
    H = len(tiles); W = len(tiles[0])
    for dy in range(-r-1, r+2):
        for dx in range(-r-1, r+2):
            if dx*dx + dy*dy <= r*r:
                tx, ty = cx+dx, cy+dy
                if 0 <= tx < W and 0 <= ty < H:
                    if tiles[ty][tx] in '01':
                        tiles[ty][tx] = tile


def _place_oval(tiles, cx, cy, rx, ry, tile_inner='5', tile_track='6', tile_access='2'):
    H = len(tiles); W = len(tiles[0])
    for dy in range(-ry-3, ry+4):
        for dx in range(-rx-3, rx+4):
            tx, ty = cx+dx, cy+dy
            if 0 <= tx < W and 0 <= ty < H:
                norm = (dx/rx)**2 + (dy/ry)**2
                if norm <= 0.55:
                    tiles[ty][tx] = tile_inner
                elif norm <= 0.95:
                    tiles[ty][tx] = tile_track
                elif norm <= 1.10:
                    tiles[ty][tx] = tile_access


def _fill_trees(tiles, x, y, w, h, only_on='01'):
    H = len(tiles); W = len(tiles[0])
    for dy in range(h):
        for dx in range(w):
            tx, ty = x+dx, y+dy
            if 0 <= tx < W and 0 <= ty < H and tiles[ty][tx] in only_on:
                tiles[ty][tx] = '8'


def _scatter_trees(tiles, x, y, w, h, density=0.4, seed=0):
    rng = _SimpleRNG(seed)
    H = len(tiles); W = len(tiles[0])
    for dy in range(h):
        for dx in range(w):
            tx, ty = x+dx, y+dy
            if 0 <= tx < W and 0 <= ty < H and tiles[ty][tx] == '0':
                if (rng.next() % 100) < int(density*100):
                    tiles[ty][tx] = '8'


def _line_bushes(tiles, x0, y0, x1, y1, every=2):
    n = max(abs(x1-x0), abs(y1-y0)) + 1
    for i in range(0, n, every):
        t = i/(n-1) if n > 1 else 0
        tx = int(x0 + (x1-x0)*t)
        ty = int(y0 + (y1-y0)*t)
        H = len(tiles); W = len(tiles[0])
        if 0 <= tx < W and 0 <= ty < H and tiles[ty][tx] in '01':
            tiles[ty][tx] = 'B'


def _organic_border(tiles, padding=3, irregularity=2, seed=0):
    H = len(tiles); W = len(tiles[0])
    rng = _SimpleRNG(seed)
    for y in range(H):
        thick = padding + (rng.next() % (irregularity+1))
        for x in range(thick):
            tiles[y][x] = 'X'
        thick = padding + (rng.next() % (irregularity+1))
        for x in range(W-thick, W):
            tiles[y][x] = 'X'
    for x in range(W):
        thick = padding + (rng.next() % (irregularity+1))
        for y in range(thick):
            tiles[y][x] = 'X'
        thick = padding + (rng.next() % (irregularity+1))
        for y in range(H-thick, H):
            tiles[y][x] = 'X'


def _tree_belt(tiles, density=0.6, seed=0):
    H = len(tiles); W = len(tiles[0])
    rng = _SimpleRNG(seed+999)
    for y in range(H):
        for x in range(W):
            if tiles[y][x] == '0':
                near = False
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        nx, ny = x+dx, y+dy
                        if 0 <= nx < W and 0 <= ny < H and tiles[ny][nx] == 'X':
                            near = True
                if near and (rng.next() % 100) < int(density*100):
                    tiles[y][x] = '8'


# ============================================================
# NIVEL 1: Fac. Matemáticas / Av. Venezuela
# ============================================================

def _build_level_1():
    W, H = 75, 58
    tiles = [['0']*W for _ in range(H)]

    # ── AV. VENEZUELA: ancha vía multicarril al oeste (5 tiles asfalto)
    for y in range(0, H):
        for dx in range(3, 9):
            tiles[y][dx] = '2'
    # Líneas de carril (decorativo via tile 'P' alternado)
    # (las pintaremos como overlay en draw)

    # ── MURO PERIMETRAL DE CONCRETO largo (separa Av.Venezuela del campus)
    for y in range(2, H-2):
        tiles[y][10] = 'W'
        tiles[y][11] = 'W'
    # Apertura: pequeña reja peatonal (decorativa, sigue siendo muro)

    # ── PABELLÓN MATEMÁTICAS — masivo y alargado escalonado (vertical)
    # Forma: 4 secciones conectadas con pequeños desfases (no rectángulo único)
    _place_stepped_building(tiles, 18, 8, [
        (0,  0, 18,  8),   # bloque norte (más ancho)
        (2,  8, 14, 10),   # bloque centro-norte
        (0, 18, 18, 10),   # bloque centro (la principal aula magna)
        (3, 28, 12,  9),   # bloque sur
        (1, 37, 16,  7),   # ala sur ancha
    ])

    # Pasillo adoquinado frontal (lado este del pabellón)
    for y in range(7, 47):
        for dx in range(36, 40):
            tiles[y][dx] = '1'

    # Camino adoquinado oeste (entre muro y pabellón)
    for y in range(8, 47):
        for dx in range(13, 17):
            tiles[y][dx] = '1'

    # ── PARQUE DE QUÍMICA al sur del pabellón (SPAWN)
    _fill_area(tiles, 18, 47, 22, 7, '1')
    # arbustos de cobertura
    for x in (19, 24, 30, 36):
        tiles[48][x] = 'B'; tiles[51][x] = 'B'
    # Bancos de árboles
    _fill_trees(tiles, 17, 46, 1, 8)
    _fill_trees(tiles, 39, 46, 1, 8)

    # ── EDIF. 7 ELÉCTRICA / 8 INDUSTRIAL al este (más pequeños)
    _place_building(tiles, 45, 12, 12, 7)
    _place_building(tiles, 45, 22, 12, 7)
    _place_building(tiles, 45, 32, 12, 7)

    # Camino transversal este→ salida
    for x in range(40, W):
        tiles[24][x] = '1'; tiles[25][x] = '1'

    # Arbustos cuadrados como cobertura
    for (bx, by) in [(42,16),(42,26),(42,36),(58,18),(58,28),(58,38)]:
        tiles[by][bx] = 'B'

    # Árboles densos dispersos (copa grande para esconderse)
    _scatter_trees(tiles, 38, 6, 7, 6, 0.35, seed=101)
    _scatter_trees(tiles, 38, 40, 7, 8, 0.4, seed=102)
    _scatter_trees(tiles, 58, 5, 10, 6, 0.45, seed=103)
    _scatter_trees(tiles, 58, 42, 10, 10, 0.5, seed=104)

    # Bordes orgánicos
    _organic_border(tiles, padding=2, irregularity=3, seed=11)
    _tree_belt(tiles, density=0.6, seed=11)

    # ── SALIDA al Nivel 2 (este, después del borde)
    for y in range(22, 28):
        for x in range(W-7, W):
            tiles[y][x] = '2'
    for y in range(22, 28):
        tiles[y][W-2] = 'E'; tiles[y][W-3] = 'E'

    # Faroles
    lamps = []
    # Av. Venezuela (postes alineados)
    for y in range(4, H, 6):
        lamps.append((6, y))
    # Muro interior
    for y in range(6, H-4, 8):
        lamps.append((12, y))
    # Pasillos del pabellón
    for y in range(10, 46, 7):
        lamps.append((37, y))
        lamps.append((44, y))
    # Salida
    lamps += [(W-7, 23), (W-7, 26)]
    # Parque de Química
    lamps += [(22, 50), (32, 50)]

    spawn = (28, 50)  # parque de Química, sur del pabellón

    guard_spawns = [
        # 2 guardias (tutorial)
        {'zone': 1, 'patrol_tiles': [(37, 10), (37, 45), (38, 45), (38, 10)]},
        {'zone': 1, 'patrol_tiles': [(45, 24), (66, 24), (66, 25), (45, 25)]},
    ]

    return {
        'W': W, 'H': H,
        'tiles': tiles, 'lamps': lamps, 'spawn': spawn,
        'guard_spawns': guard_spawns, 'cars': [],
        'name': 'Nivel 1 — Fac. Matemáticas',
        'hint': 'Tutorial: cruza el campus al este (Av. Venezuela queda atrás)',
        'overlays': ['venezuela_lanes'],
    }


# ============================================================
# NIVEL 2: Comedor / Estadio UNMSM
# ============================================================

def _build_level_2():
    W, H = 80, 60
    tiles = [['0']*W for _ in range(H)]

    # ── ESTADIO MONUMENTAL (mitad superior del óvalo en la parte INFERIOR del mapa)
    # Centro abajo, así solo se ve la mitad superior
    _place_oval(tiles, cx=40, cy=H+8, rx=30, ry=18)

    # ── ESTACIONAMIENTO EN ABANICO (semicírculo) sobre el estadio
    cx_p, cy_p = 40, 30
    R_OUT, R_IN = 22, 10
    H2 = H; W2 = W
    for dy in range(-R_OUT, 1):
        for dx in range(-R_OUT, R_OUT+1):
            d2 = dx*dx + dy*dy
            tx, ty = cx_p+dx, cy_p+dy
            if 0 <= tx < W2 and 0 <= ty < H2 and dy <= 0:
                if R_IN*R_IN <= d2 <= R_OUT*R_OUT:
                    tiles[ty][tx] = '2'

    # ── COMEDOR UNIVERSITARIO arriba (2 bloques rectangulares masivos)
    _place_building(tiles, 8, 4, 22, 9)
    _place_building(tiles, 33, 4, 18, 8)
    _place_building(tiles, 54, 4, 20, 9)
    # Pasillo entre comedores
    for x in range(8, 75):
        tiles[14][x] = '1'

    # ── VÍAS VEHICULARES amplias conectando estacionamiento y comedor
    for y in range(14, 31):
        for dx in range(36, 45):
            tiles[y][dx] = '2'
    # Vía perimetral este al estadio
    for y in range(20, 50):
        for dx in range(70, 75):
            tiles[y][dx] = '2'
    # Vía perimetral oeste
    for y in range(20, 50):
        for dx in range(5, 9):
            tiles[y][dx] = '2'

    # ── Camino peatonal central
    for x in range(15, 70):
        tiles[18][x] = '1'

    # Arbustos como cobertura entre estacionamiento y vía
    for x in (15, 22, 30, 50, 58, 65):
        tiles[28][x] = 'B'; tiles[29][x] = 'B'

    # Árboles dispersos
    _scatter_trees(tiles, 8, 16, 25, 5, 0.3, seed=201)
    _scatter_trees(tiles, 50, 16, 25, 5, 0.3, seed=202)
    _scatter_trees(tiles, 0, 25, 6, 30, 0.5, seed=203)
    _scatter_trees(tiles, 73, 25, 6, 30, 0.5, seed=204)

    _organic_border(tiles, padding=2, irregularity=3, seed=22)
    _tree_belt(tiles, density=0.55, seed=22)

    # ENTRADA desde Nivel 1 (lado oeste) tras el borde
    for y in (24, 25, 26):
        for x in range(0, 9):
            tiles[y][x] = '1'

    # SALIDA al Nivel 3 (lado norte-derecha) tras el borde
    for y in range(0, 6):
        for x in range(60, 68):
            tiles[y][x] = '2'
    for x in range(60, 68):
        tiles[1][x] = 'E'; tiles[2][x] = 'E'

    lamps = []
    # Estacionamiento (perímetro circular)
    for ang in range(180, 361, 30):
        a = math.radians(ang)
        lx = int(cx_p + (R_OUT-2) * math.cos(a))
        ly = int(cy_p + (R_OUT-2) * math.sin(a))
        if ly < cy_p: lamps.append((lx, ly))
    # Comedor
    for x in range(10, 75, 8):
        lamps.append((x, 15))
    # Vías perimetrales
    for y in range(22, 50, 7):
        lamps.append((6, y)); lamps.append((72, y))
    # Salida y entrada
    lamps += [(63, 4), (5, 25), (63, 7)]

    spawn = (5, 25)

    guard_spawns = [
        {'zone': 2, 'patrol_tiles': [(15, 18), (65, 18), (65, 19), (15, 19)]},
        {'zone': 2, 'patrol_tiles': [(28, 25), (52, 25), (52, 26), (28, 26)]},
        {'zone': 2, 'patrol_tiles': [(70, 22), (70, 48), (72, 48), (72, 22)]},
    ]
    # Autos en estacionamiento abanico (posiciones radiales)
    car_positions = []
    for i, ang in enumerate(range(195, 346, 22)):
        a = math.radians(ang)
        cx = int(cx_p + (R_OUT-5) * math.cos(a))
        cy = int(cy_p + (R_OUT-5) * math.sin(a))
        if cy < cy_p: car_positions.append((cx, cy))

    return {
        'W': W, 'H': H,
        'tiles': tiles, 'lamps': lamps, 'spawn': spawn,
        'guard_spawns': guard_spawns, 'cars': car_positions,
        'name': 'Nivel 2 — Estadio UNMSM',
        'hint': 'Cruza el estacionamiento y sal por el norte hacia la Plaza',
        'overlays': ['parking_diagonals', 'stadium_lines'],
    }


# ============================================================
# NIVEL 3: Plaza Cívica / Biblioteca / Rectorado
# ============================================================

def _build_level_3():
    W, H = 70, 58
    tiles = [['0']*W for _ in range(H)]

    # ── PLAZA CÍVICA: gran círculo de adoquines al centro
    PCX, PCY, PR = 35, 28, 12
    _place_circle_plaza(tiles, PCX, PCY, PR, tile='1')
    # Estatua central
    _set(tiles, PCX, PCY, 'S')
    # Anillo decorativo (arbustos cuadrados rodeando la plaza)
    for ang in range(0, 360, 25):
        a = math.radians(ang)
        bx = int(PCX + (PR+2) * math.cos(a))
        by = int(PCY + (PR+2) * math.sin(a))
        if 0 < bx < W and 0 < by < H and tiles[by][bx] == '0':
            tiles[by][bx] = 'B'

    # ── RECTORADO en forma de "U" abierta hacia la plaza (al NORTE)
    _place_u_building(tiles, 24, 4, 22, 11, opening_w=8, opening_dir='S')

    # ── BIBLIOTECA CENTRAL: bloques rectangulares superpuestos irregulares (al SUR)
    _place_building(tiles, 22, 42, 12, 8)
    _place_building(tiles, 30, 45, 14, 9)
    _place_building(tiles, 42, 42, 12, 7)
    _place_building(tiles, 26, 50, 8, 5)

    # ── Av. Amézaga al este (vertical, asfalto)
    for y in range(4, H-4):
        for dx in range(60, 64):
            tiles[y][dx] = '2'

    # ── Edificios este (22 Med.Trop, 23 Psic, 24 Minas)
    _place_building(tiles, 52, 6, 7, 6)
    _place_building(tiles, 52, 14, 7, 6)
    _place_building(tiles, 52, 22, 7, 6)

    # Caminos radiales desde la plaza
    for ang in (0, 60, 120, 180, 240, 300):
        a = math.radians(ang)
        for r in range(PR, PR+8):
            tx = int(PCX + r*math.cos(a))
            ty = int(PCY + r*math.sin(a))
            if 0 < tx < W and 0 < ty < H and tiles[ty][tx] == '0':
                tiles[ty][tx] = '1'

    # Camino adoquinado plaza→biblio
    for y in range(40, 55):
        tiles[y][PCX] = '1'; tiles[y][PCX+1] = '1'

    # ── HUACA SAN MARCOS: zona arqueológica esquina noroeste (área verde con plataformas)
    _fill_area(tiles, 4, 6, 16, 14, '0')
    # Plataformas de la huaca (dos bloques bajos)
    _place_building(tiles, 6, 9, 7, 5)
    _place_building(tiles, 12, 13, 7, 5)
    _scatter_trees(tiles, 4, 6, 16, 14, 0.3, seed=301)

    # Árboles decorativos
    _scatter_trees(tiles, 4, 35, 18, 18, 0.4, seed=302)
    _scatter_trees(tiles, 47, 30, 5, 18, 0.4, seed=303)

    _organic_border(tiles, padding=2, irregularity=3, seed=33)
    _tree_belt(tiles, density=0.55, seed=33)

    # ENTRADA desde Nivel 2 (lado sur)
    for y in range(H-7, H):
        for x in range(30, 38):
            tiles[y][x] = '2'

    # SALIDA al Nivel 4 (lado este)
    for y in range(26, 32):
        for x in range(W-7, W):
            tiles[y][x] = '2'
    for y in range(26, 32):
        tiles[y][W-2] = 'E'; tiles[y][W-3] = 'E'

    lamps = []
    # Plaza (4 cardinales)
    lamps += [(PCX, PCY-PR), (PCX, PCY+PR), (PCX-PR, PCY), (PCX+PR, PCY)]
    # Esquinas plaza
    for ang in (45, 135, 225, 315):
        a = math.radians(ang)
        lamps.append((int(PCX + (PR-2)*math.cos(a)), int(PCY + (PR-2)*math.sin(a))))
    # Av Amézaga
    for y in range(6, H-4, 7):
        lamps.append((58, y))
    # Rectorado / Biblio
    lamps += [(28, 14), (40, 14), (28, 42), (45, 42)]
    # Salida y entrada
    lamps += [(W-7, 27), (W-7, 30), (33, H-5)]

    spawn = (33, H-5)

    guard_spawns = [
        # 3 guardias (zona 3)
        {'zone': 3, 'patrol_tiles': [(PCX-PR, PCY), (PCX+PR, PCY), (PCX+PR, PCY+1), (PCX-PR, PCY+1)]},
        {'zone': 3, 'patrol_tiles': [(28, 18), (42, 18), (42, 19), (28, 19)]},
        {'zone': 3, 'patrol_tiles': [(28, 40), (50, 40), (50, 41), (28, 41)]},
    ]

    return {
        'W': W, 'H': H,
        'tiles': tiles, 'lamps': lamps, 'spawn': spawn,
        'guard_spawns': guard_spawns, 'cars': [],
        'name': 'Nivel 3 — Plaza Cívica / Biblioteca',
        'hint': 'Cruza la Plaza Cívica y sal al este hacia Sistemas',
        'overlays': ['plaza_circle'],
    }


# ============================================================
# NIVEL 4: Fac. Sistemas / Puerta 7 (FINAL)
# ============================================================

def _build_level_4():
    W, H = 65, 55
    tiles = [['0']*W for _ in range(H)]

    # ── FAC. SISTEMAS en forma de CRUZ GRUESA / "T"
    # Brazo horizontal grande + stem vertical hacia el norte
    _place_building(tiles, 18, 16, 22, 8)   # brazo horizontal
    _place_building(tiles, 25, 6, 8, 10)    # stem norte
    _place_building(tiles, 26, 24, 6, 8)    # pequeño stem sur (cruz)

    # ── Edificios secundarios (Centro Informática, Educación, Clínica, Odonto)
    _place_building(tiles, 6, 32, 11, 8)    # 17 Centro Info
    _place_building(tiles, 19, 35, 10, 7)   # 18 Educación
    _place_building(tiles, 32, 35, 10, 7)   # 16 Clínica
    _place_building(tiles, 44, 6, 12, 9)    # 20 Odontología

    # ── SENDEROS de concreto en DIAGONAL hacia la esquina inferior derecha (Puerta 7)
    # Sendero diagonal 1: desde el centro hacia esquina SE
    for i in range(0, 30):
        tx = 30 + i
        ty = 25 + i
        if 0 <= tx < W-3 and 0 <= ty < H-3:
            tiles[ty][tx] = '1'
            if tx+1 < W: tiles[ty][tx+1] = '1'
    # Sendero diagonal 2: desde Sistemas norte hacia SE
    for i in range(0, 25):
        tx = 22 + i
        ty = 24 + i
        if 0 <= tx < W-3 and 0 <= ty < H-3 and tiles[ty][tx] == '0':
            tiles[ty][tx] = '1'

    # Camino central E-O
    for x in range(8, 56):
        tiles[28][x] = '1'

    # ── REJA PERIMETRAL en el este y sur
    for y in range(2, H-2):
        tiles[y][W-3] = 'W'
    for x in range(2, W-2):
        tiles[H-3][x] = 'W'

    # ── PUERTA 7 — gran portón vehicular y peatonal en esquina SE entreabierto
    # Apertura en la reja (esquina inferior derecha)
    for y in range(H-8, H-3):
        tiles[y][W-3] = 'G'   # portón vehicular vertical
    for x in range(W-10, W-3):
        tiles[H-3][x] = 'G'   # portón peatonal horizontal
    # Asfalto exterior detrás (Calle Germán Amézaga)
    for y in range(H-8, H):
        for x in range(W-2, W):
            tiles[y][x] = '2'
    for y in range(H-2, H):
        for x in range(W-12, W):
            tiles[y][x] = '2'

    # ── CÁMARAS de seguridad en paredes
    _set(tiles, 18, 16, 'C')   # esquina NW Sistemas
    _set(tiles, 39, 16, 'C')   # esquina NE Sistemas
    _set(tiles, 39, 23, 'C')
    _set(tiles, 56, 6, 'C')    # esquina Odonto
    _set(tiles, W-4, H-12, 'C')  # vigilando puerta 7

    # Jardines irregulares con árboles densos y arbustos
    _scatter_trees(tiles, 4, 4, 12, 10, 0.4, seed=401)
    _scatter_trees(tiles, 4, 42, 50, 8, 0.35, seed=402)
    _scatter_trees(tiles, 42, 16, 4, 18, 0.4, seed=403)
    # Arbustos cuadrados como cobertura cerca de Puerta 7
    for x in (40, 44, 48, 52):
        tiles[44][x] = 'B'; tiles[45][x] = 'B'

    _organic_border(tiles, padding=2, irregularity=2, seed=44)
    _tree_belt(tiles, density=0.5, seed=44)

    # ENTRADA desde Nivel 3 (lado oeste) tras el borde
    for y in (27, 28, 29):
        for x in range(0, 9):
            tiles[y][x] = '1'

    # PUERTA 7 sigue siendo 'G' tras el borde — re-asegura
    for y in range(H-8, H-3):
        tiles[y][W-3] = 'G'
        tiles[y][W-2] = 'E'

    lamps = []
    # Camino central
    for x in range(8, 56, 8):
        lamps.append((x, 28))
    # Diagonal hacia Puerta 7 (faroles dorados intensos)
    for i in range(0, 30, 5):
        tx, ty = 30+i, 25+i
        if tx < W-3 and ty < H-3:
            lamps.append((tx, ty))
    # Esquinas Sistemas
    lamps += [(18, 16), (39, 16), (25, 24), (32, 24)]
    # Cerca de Puerta 7 (intensos)
    lamps += [(W-5, H-6), (W-5, H-9), (W-7, H-4)]
    # Entrada oeste
    lamps += [(4, 28), (10, 28)]

    spawn = (5, 28)

    guard_spawns = [
        {'zone': 4, 'patrol_tiles': [(8, 28), (54, 28), (54, 29), (8, 29)]},
        {'zone': 4, 'patrol_tiles': [(20, 33), (50, 33), (50, 34), (20, 34)]},
        {'zone': 4, 'patrol_tiles': [(W-6, 6), (W-6, H-10), (W-7, H-10), (W-7, 6)]},
        {'zone': 4, 'patrol_tiles': [(40, H-7), (W-6, H-7), (W-6, H-6), (40, H-6)]},
    ]

    return {
        'W': W, 'H': H,
        'tiles': tiles, 'lamps': lamps, 'spawn': spawn,
        'guard_spawns': guard_spawns, 'cars': [],
        'name': 'Nivel 4 — Fac. Sistemas / Puerta 7',
        'hint': '¡Cruza al sureste, atraviesa la Puerta 7 y escapa!',
        'overlays': ['puerta7_glow'],
    }


_LEVEL_BUILDERS = {1: _build_level_1, 2: _build_level_2,
                   3: _build_level_3, 4: _build_level_4}


def total_levels():
    return len(_LEVEL_BUILDERS)


# ============================================================
# CLASE ProceduralMap
# ============================================================

class ProceduralMap:
    TILE_COLORS = {
        '0': (28, 55, 22), '1': (60, 52, 42), '2': (38, 38, 45),
        '3': (75, 65, 85), '4': (60, 52, 70), '5': (40, 90, 40),
        '6': (95, 70, 55), '7': (20, 60, 110), '8': (22, 80, 22),
        'W': (100, 100, 105), 'B': (20, 65, 25), 'C': (200, 40, 40),
        'S': (170, 160, 150), 'G': (180, 150, 70), 'R': (85, 75, 95),
        'X': (8, 6, 14), 'E': (0, 200, 90),
    }
    SOLID_TILES = {'3', 'W', 'B', 'C', 'S', 'R', 'X'}

    TILE_TO_SPRITE = {
        '0': 'grass', '1': 'path', '2': 'asphalt',
        '3': 'building_wall', '4': 'building_floor',
        '5': 'stadium_grass', '6': 'track', '7': 'water',
        '8': 'tree', 'W': 'concrete_wall', 'B': 'bush',
        'C': 'camera_panel', 'S': 'statue', 'G': 'gate',
        'R': 'roof', 'E': 'path',
    }

    def __init__(self, level_number=1):
        self.level_number = max(1, min(total_levels(), level_number))
        data = _LEVEL_BUILDERS[self.level_number]()
        self.tiles = data['tiles']
        self.lamp_tile_positions = data['lamps']
        self._spawn_tile = data['spawn']
        self._guard_spawn_tiles = data['guard_spawns']
        self._car_tiles = data['cars']
        self.level_name = data['name']
        self.level_hint = data['hint']
        self._overlays = data.get('overlays', [])

        self.height = len(self.tiles)
        self.width = len(self.tiles[0])
        self.tile_size = TILE_SIZE
        self.pixel_width = self.width * self.tile_size
        self.pixel_height = self.height * self.tile_size

        self.sprite_gen = SpriteGenerator()
        self._tile_cache = {}

        self.surface = self._render()

        self.collision_rects = self._build_collision()
        self.lamp_positions = self._get_lamp_positions()
        self.exit_rect = self._get_exit_rect()
        self.spawn_point = self._tile_to_pixel(*self._spawn_tile)
        self.guard_spawns = self._compile_guard_spawns()
        self.car_positions = [self._tile_to_pixel(tx, ty) for tx, ty in self._car_tiles]

    def _tile_to_pixel(self, tx, ty):
        ts = self.tile_size
        return pygame.math.Vector2(tx*ts + ts//2, ty*ts + ts//2)

    def _get_tile_surface(self, ch):
        if ch in self._tile_cache:
            return self._tile_cache[ch]
        if ch == 'X':
            surf = pygame.Surface((self.tile_size, self.tile_size))
            surf.fill(self.TILE_COLORS['X'])
        else:
            tile_name = self.TILE_TO_SPRITE.get(ch, 'grass')
            surf = self.sprite_gen.get_tile(tile_name)
        if ch == 'E':
            surf = surf.copy()
            overlay = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)
            overlay.fill((0, 200, 90, 110))
            surf.blit(overlay, (0, 0))
        self._tile_cache[ch] = surf
        return surf

    def _render(self):
        surf = pygame.Surface((self.pixel_width, self.pixel_height))
        surf.fill(COLOR_BACKGROUND)
        ts = self.tile_size
        for ry, row in enumerate(self.tiles):
            for rx, ch in enumerate(row):
                surf.blit(self._get_tile_surface(ch), (rx*ts, ry*ts))
        # Overlays decorativos sobre el render base
        self._draw_overlays(surf)
        self._draw_zone_labels(surf)
        return surf

    def _draw_overlays(self, surf):
        ts = self.tile_size
        for ov in self._overlays:
            if ov == 'venezuela_lanes':
                # Líneas blancas centrales de Av. Venezuela (en x=6 columna)
                for y in range(0, self.pixel_height, 24):
                    pygame.draw.rect(surf, (200, 200, 200),
                                     (6*ts + 14, y+4, 4, 14))
            elif ov == 'parking_diagonals':
                # Líneas blancas diagonales en el estacionamiento abanico
                cx_p, cy_p = 40*ts, 30*ts
                for ang in range(180, 361, 12):
                    a = math.radians(ang)
                    x1 = cx_p + 11*ts*math.cos(a); y1 = cy_p + 11*ts*math.sin(a)
                    x2 = cx_p + 21*ts*math.cos(a); y2 = cy_p + 21*ts*math.sin(a)
                    if y1 <= cy_p + 4 and y2 <= cy_p + 4:
                        pygame.draw.line(surf, (220, 220, 220), (x1, y1), (x2, y2), 2)
            elif ov == 'stadium_lines':
                # Líneas del campo del estadio (en la mitad visible)
                cx, cy = 40*ts, (self.height+8)*ts
                for ry in (-13, -7, 0):
                    pygame.draw.ellipse(surf, (200, 200, 200),
                                        (cx-28*ts, cy+ry*ts-2, 56*ts, 4), 1)
            elif ov == 'plaza_circle':
                # Círculos concéntricos decorativos en la Plaza Cívica
                pcx, pcy = 35*ts, 28*ts
                for r in (4*ts, 8*ts, 11*ts):
                    pygame.draw.circle(surf, (90, 80, 70), (pcx, pcy), r, 2)
                # Cruz radial
                for ang in (0, 90, 180, 270):
                    a = math.radians(ang)
                    pygame.draw.line(surf, (90, 80, 70),
                                     (pcx, pcy),
                                     (pcx + int(11*ts*math.cos(a)),
                                      pcy + int(11*ts*math.sin(a))), 2)
            elif ov == 'puerta7_glow':
                # Halo dorado intenso alrededor de la Puerta 7
                px = (self.width-3)*ts + ts//2
                py = (self.height-6)*ts + ts//2
                glow = pygame.Surface((10*ts, 10*ts), pygame.SRCALPHA)
                for r in range(5*ts, 0, -1*ts):
                    a = max(0, 80 - r//4)
                    pygame.draw.circle(glow, (255, 220, 100, a),
                                       (5*ts, 5*ts), r)
                surf.blit(glow, (px - 5*ts, py - 5*ts), special_flags=pygame.BLEND_RGB_ADD)

    def _draw_zone_labels(self, surf):
        font = pygame.font.SysFont('monospace', 11, bold=True)
        ts = self.tile_size
        title = font.render(self.level_name, True, (255, 230, 130))
        title.set_alpha(200)
        surf.blit(title, (5*ts, 1*ts))
        labels = {
            1: [
                (4, 1, "AV. VENEZUELA", (160, 160, 180)),
                (18, 9, "FAC. MATEMATICAS", (255, 230, 100)),
                (45, 13, "7. ELECTRICA", (200, 200, 220)),
                (45, 23, "8. INDUSTRIAL", (200, 200, 220)),
                (20, 50, "PARQUE QUIMICA", (255, 220, 120)),
                (66, 23, "→ ZONA 2", (0, 255, 100)),
            ],
            2: [
                (8, 5, "COMEDOR UNIVERSITARIO", (255, 200, 130)),
                (22, 22, "ESTACIONAMIENTO", (180, 180, 200)),
                (32, 50, "ESTADIO UNMSM", (130, 255, 150)),
                (61, 4, "→ ZONA 3", (0, 255, 100)),
            ],
            3: [
                (4, 7, "HUACA SAN MARCOS", (220, 200, 130)),
                (24, 5, "RECTORADO", (130, 180, 255)),
                (28, 17, "PLAZA CIVICA", (255, 240, 120)),
                (24, 41, "BIBLIOTECA P. ZULEN", (200, 255, 120)),
                (52, 8, "22 MED", (180, 220, 255)),
                (52, 16, "23 PSIC", (180, 220, 255)),
                (52, 24, "24 MINAS", (180, 220, 255)),
                (60, 27, "→ ZONA 4", (0, 255, 100)),
            ],
            4: [
                (20, 17, "FAC. SISTEMAS", (255, 150, 200)),
                (44, 7, "20 ODONTOLOGIA", (200, 200, 220)),
                (6, 33, "17 INFO", (200, 200, 220)),
                (19, 36, "18 EDU", (200, 200, 220)),
                (32, 36, "16 CLINICA", (200, 200, 220)),
                (45, 50, "PUERTA 7 →", (255, 220, 80)),
                (54, 2, "AV. AMEZAGA", (160, 160, 180)),
            ],
        }
        for tx, ty, text, color in labels.get(self.level_number, []):
            t = font.render(text, True, color)
            t.set_alpha(220)
            surf.blit(t, (tx*ts, ty*ts))

    def _build_collision(self):
        rects = []
        ts = self.tile_size
        for ry, row in enumerate(self.tiles):
            for rx, ch in enumerate(row):
                if ch in self.SOLID_TILES:
                    rects.append(pygame.Rect(rx*ts, ry*ts, ts, ts))
        return rects

    def _get_lamp_positions(self):
        ts = self.tile_size
        return [(lx*ts + ts//2, ly*ts + ts//2) for lx, ly in self.lamp_tile_positions]

    def _get_exit_rect(self):
        ts = self.tile_size
        exits = []
        for ry, row in enumerate(self.tiles):
            for rx, ch in enumerate(row):
                if ch == 'E':
                    exits.append(pygame.Rect(rx*ts, ry*ts, ts, ts))
        if exits:
            x0 = min(r.x for r in exits); y0 = min(r.y for r in exits)
            x1 = max(r.right for r in exits); y1 = max(r.bottom for r in exits)
            return pygame.Rect(x0, y0, x1-x0, y1-y0)
        return pygame.Rect(0, 0, 1, 1)

    def _compile_guard_spawns(self):
        ts = self.tile_size
        result = []
        for s in self._guard_spawn_tiles:
            patrol_px = [(tx*ts + ts//2, ty*ts + ts//2) for tx, ty in s['patrol_tiles']]
            ftx, fty = s['patrol_tiles'][0]
            result.append({
                'pos': pygame.math.Vector2(ftx*ts + ts//2, fty*ts + ts//2),
                'zone': s['zone'],
                'patrol': patrol_px,
            })
        return result

    def draw(self, screen, camera):
        ox, oy = camera.get_offset()
        screen.blit(self.surface, (ox, oy))

    def get_tile_at(self, world_x, world_y):
        tx = int(world_x // self.tile_size)
        ty = int(world_y // self.tile_size)
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.tiles[ty][tx]
        return 'X'

    def get_zone_at(self, world_x, world_y):
        return self.level_number

    def is_final_level(self):
        return self.level_number >= total_levels()
