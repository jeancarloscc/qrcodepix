"""
QR Code PIX Generator
~~~~~~~~~~~~~~~~~~~~~

Biblioteca Python para geração de QR Codes PIX conforme especificação do Banco Central.

Uso básico:

    >>> from qrcodepix.core.payload import build_pix_payload
    >>> from qrcodepix.generator.qr import save_qr_files
    >>> 
    >>> payload = build_pix_payload(
    ...     chave_pix="seuemail@exemplo.com",
    ...     merchant_name="João Silva",
    ...     merchant_city="São Paulo",
    ...     valor=10.50
    ... )
    >>> 
    >>> png_path, svg_path = save_qr_files(payload)

:copyright: (c) 2025 by Jean Carlos.
:license: MIT, see LICENSE for more details.
"""

__version__ = "1.1.1"
__author__ = "Jean Carlos"
__email__ = "jeancc.costa@gmail.com"

from qrcodepix.core.payload import build_pix_payload
from qrcodepix.generator.qr import save_qr_files

__all__ = ["build_pix_payload", "save_qr_files", "__version__"]
