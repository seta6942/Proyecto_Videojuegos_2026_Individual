#!/usr/bin/env python3
"""
Sombras en la UNMSM
Punto de entrada principal del juego.

Estudiantes: 
- Tapia Acosta Sandro Estanislao
- Pariguana Angulo Carlos Josue 
- Ibañez Sanchez Marlon Alexis.
"""

import sys
import os

# Asegurar que el directorio del juego esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
