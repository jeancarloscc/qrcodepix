"""Geração do QR Code em PNG e SVG.
Tenta usar `segno` (recomendado). Se não encontrado, faz fallback para `qrcode`.
"""
from typing import Tuple


def save_qr_files(payload: str, filename_base: str = "pix_qr", scale: int = 8, border: int = 4) -> Tuple[str, str]:
    png_path = f"{filename_base}.png"
    svg_path = f"{filename_base}.svg"

    try:
        import segno

        qr = segno.make(payload, micro=False)
        qr.save(png_path, scale=scale, border=border)

        # Para SVG, multiplicar scale por 3 para garantir tamanho adequado
        # SVG renderiza em unidades diferentes, então precisa de scale maior
        svg_scale = scale * 3
        qr.save(svg_path, scale=svg_scale, border=border,
                xmldecl=False, svgclass=None)
        return png_path, svg_path

    except Exception:
        # fallback para qrcode (pil + svg)
        try:
            import qrcode
            from qrcode.image.svg import SvgImage

            qr = qrcode.QRCode(border=border)
            qr.add_data(payload)
            qr.make(fit=True)
            img = qr.make_image()
            img.save(png_path)

            qr_svg = qrcode.make(payload, image_factory=SvgImage)
            qr_svg.save(svg_path)

            return png_path, svg_path

        except Exception as exc:
            raise RuntimeError(
                "Nenhuma biblioteca de QR disponível. Instale 'segno' ou 'qrcode[pil] qrcode[svg]'."
            ) from exc
