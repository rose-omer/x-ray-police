"""X-Ray Polisi başlatıcı.

Kullanım:  python xray-detect.py
Kod `xray_polisi/` paketindedir.
"""
import sys

from xray_polisi.app import main

if __name__ == "__main__":
    sys.exit(main())
