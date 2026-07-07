"""Geração do QR Code em PNG e SVG.
Tenta usar `segno` (recomendado). Se não encontrado, faz fallback para `qrcode`.
"""
from typing import Tuple

# Nível de correção de erro recomendado pelo Manual do BR Code (Banco Central): M.
DEFAULT_ERROR_CORRECTION = "m"

_QRCODE_ERROR_LEVELS = None  # populado sob demanda (import tardio de `qrcode`)


def _qrcode_error_level(error: str):
    global _QRCODE_ERROR_LEVELS
    import qrcode.constants as c

    if _QRCODE_ERROR_LEVELS is None:
        _QRCODE_ERROR_LEVELS = {
            "l": c.ERROR_CORRECT_L,
            "m": c.ERROR_CORRECT_M,
            "q": c.ERROR_CORRECT_Q,
            "h": c.ERROR_CORRECT_H,
        }
    return _QRCODE_ERROR_LEVELS[error.lower()]


def save_qr_files(
    payload: str,
    filename_base: str = "pix_qr",
    scale: int = 8,
    border: int = 4,
    error: str = DEFAULT_ERROR_CORRECTION,
) -> Tuple[str, str]:
    """Gera PNG e SVG do QR Code. `error` é o nível de correção de erro EMV (l/m/q/h)."""
    png_path = f"{filename_base}.png"
    svg_path = f"{filename_base}.svg"

    try:
        import segno
    except ModuleNotFoundError:
        segno = None

    if segno is not None:
        qr = segno.make(payload, micro=False, error=error)
        qr.save(png_path, scale=scale, border=border)

        # Para SVG, multiplicar scale por 3 para garantir tamanho adequado
        # SVG renderiza em unidades diferentes, então precisa de scale maior
        svg_scale = scale * 3
        qr.save(svg_path, scale=svg_scale, border=border,
                xmldecl=False, svgclass=None)
        return png_path, svg_path

    # fallback para qrcode (pil + svg) — só chega aqui se `segno` não estiver instalado
    try:
        import qrcode
        from qrcode.image.svg import SvgImage
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Nenhuma biblioteca de QR disponível. Instale 'segno' ou 'qrcode[pil,svg]'."
        ) from exc

    error_correction = _qrcode_error_level(error)

    qr = qrcode.QRCode(border=border, error_correction=error_correction)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image()
    img.save(png_path)

    qr_svg = qrcode.make(payload, image_factory=SvgImage, error_correction=error_correction)
    qr_svg.save(svg_path)

    return png_path, svg_path
