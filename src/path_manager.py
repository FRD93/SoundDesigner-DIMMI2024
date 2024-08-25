import os
import sys


def resource_path(relative_path):
    """Ottiene il percorso del file necessario, considerando il pacchetto PyInstaller."""
    try:
        # PyInstaller crea una cartella temporanea _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


print(f"resource_path is {resource_path('')}")
STYLE_PATH = resource_path("style.json")
STYLESHEET_PATH = resource_path("style.stylesheet")
CONFIG_PATH = resource_path("config.ini")
WIDGETS_PATH = resource_path("")
GRAPHICS_PATH = resource_path("graphic_files/")
