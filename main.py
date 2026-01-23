#!/usr/bin/env python3
import sys
import os

# Ensure the subfolder is in the path
sys.path.insert(0, os.path.dirname(__file__))

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio

# IMPORTANT: Import the APPLICATION class
from colormydesktop.lib_gui import ColorMyDesktopApp

def main():
    #  Initialize the Application (This is the D-Bus process)
    app = ColorMyDesktopApp()
    
 
    return app.run([])

if __name__ == "__main__":
    sys.exit(main())

