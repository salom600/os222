"""SalomOS Hardware Manager — auto-detect GPU, NIC, and storage, install drivers.

Module structure:
- detectors/: GPU, NIC, storage, audio
- drivers/: nvidia, intel, amd, realtek, broadcom, atheros
- ui/: PyQt6 GUI window
- cli.py: command-line entry-point
- daemon.py: background service that auto-runs at first boot
"""
__version__ = "1.0.0"
__all__ = ["__version__"]
