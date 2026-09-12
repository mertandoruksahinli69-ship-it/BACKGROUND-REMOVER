# -*- coding: utf-8 -*-
"""Çift tıkla çalıştır: konsol/terminal hiç açılmaz (pythonw ile çalışır)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from background_remover import main

if __name__ == "__main__":
    main()
