# Sombras en la UNMSM
## Infiltración Táctica Nocturna en la Ciudad Universitaria

**Estudiante:** Tapia Acosta Sandro Estanislao  
**Institución:** Universidad Nacional Mayor de San Marcos - Fac. Ciencias Matemáticas  
**Año:** 2026

---

## Cómo ejecutar

```bash
cd Sombras
python main.py
```

## Controles

| Tecla | Acción |
|-------|--------|
| WASD / Flechas | Mover a Melvin |
| SHIFT | Modo sigilo (lento y silencioso) |
| CTRL | Sprint (rápido y ruidoso) |
| SPACE | Ocultarse (cerca de cobertura) |
| Clic Derecho | Lanzar piedra al punto indicado |
| Q | Activar alarma del auto más cercano |
| ESC | Pausa |
| R | Reiniciar (en Game Over o Pausa) |
| F1 | Info de posición (debug) |

## Zonas del Campus

1. **Zona 1** — Fac. Matemáticas / Av. Venezuela (punto de inicio)
2. **Zona 2** — Comedor / Alrededores del Estadio UNMSM
3. **Zona 3** — Biblioteca Pedro Zulen / Plaza Cívica / Rectorado
4. **Zona 4** — Fac. Sistemas / Jardines / **Puerta 7 (EXIT)**

## Sistema de Alerta Global

- **0-40%**: Guardias en patrulla normal
- **41-70%**: Alerta Media — guardias más rápidos
- **71-99%**: Alerta Alta — guardias muy rápidos
- **100%**: GAME OVER — llegaron los refuerzos

## Mecánicas

- **Cono de visión tricolor**: Verde (patrulla) → Amarillo (sospecha) → Rojo (persecución)
- **Piedras** (máx. 3): Distraen guardias al punto de impacto por 4 segundos
- **Alarma de auto**: Distrae guardias en radio de 180px por 8 segundos (uso único por auto)
- **Sigilo**: SHIFT hace a Melvin silencioso (no activa detección auditiva)
- **Ocultarse**: SPACE hace a Melvin invisible a guardias

## Arquitectura

```
game/
├── main.py           # Punto de entrada
├── requirements.txt
└── src/
    ├── settings.py   # Constantes y configuración global
    ├── game.py       # Loop principal y coordinación
    ├── player.py     # Jugador (Melvin)
    ├── guard.py      # IA de guardias (FSM 3 estados)
    ├── camera.py     # Cámara con seguimiento suave
    ├── tilemap.py    # Carga de TMX (pytmx)
    ├── map_generator.py  # Mapa procedimental del campus UNMSM
    ├── lighting.py   # Iluminación nocturna
    ├── hud.py        # HUD y UI
    └── sprites.py    # Generador de sprites pixel art
```
