#!/usr/bin/env python3
"""
Build script for the GUI application using PyInstaller
"""

import PyInstaller.__main__
import os
import sys

def build_gui():
    """Build the GUI application"""

    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # PyInstaller arguments
    args = [
        'rw_tunnel_gui.py',  # Main script
        '--onefile',         # Single executable
        '--name=rw-local-tunnel-gui',  # Output name
        '--noconsole',       # No console window for GUI
        '--add-data=README.md:.',      # Include README
        '--add-data=LICENSE:.',        # Include LICENSE

        # Hidden imports for dependencies
        '--hidden-import=customtkinter',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=psutil._psutil_linux',
        '--hidden-import=psutil._psutil_posix',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=pystray',

        # Exclude unnecessary modules
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=scipy',
        '--exclude-module=pandas',
        '--exclude-module=jupyter',

        # Clean build
        '--clean',

        # Output directory
        '--distpath=dist',
        '--workpath=build',
        '--specpath=.',
    ]

    # Run PyInstaller
    PyInstaller.__main__.run(args)

    print("\n✅ GUI build complete! Check dist/rw-local-tunnel-gui")

if __name__ == "__main__":
    build_gui()