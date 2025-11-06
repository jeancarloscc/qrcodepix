from typing import Optional, Tuple

POLY = 0x1021
INIT = 0xFFFF


def crc16(payload_bytes: bytes) -> str:
    """CRC-16/CCITT (polynomial 0x1021, init 0xFFFF). Retorna 4 hex maiúsculo."""
    crc = INIT
    for b in payload_bytes:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ POLY) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _emv_field_bytes(tag: str, value: str) -> bytes:
    """Retorna bytes do campo tag+len(2d em bytes)+value(utf-8)."""
    v_bytes = value.encode("utf-8")
    length = len(v_bytes)
    return f"{tag}{length:02d}".encode("utf-8") + v_bytes


def _emv_field_str(tag: str, value: str) -> str:
    """Auxiliar que retorna string (útil se preferir trabalhar em str)."""
    return _emv_field_bytes(tag, value).decode("utf-8")


def build_pix_payload(
    chave_pix: str,
    merchant_name: str,
    merchant_city: str,
    valor: Optional[float] = None,
    txid: Optional[str] = None,
    description: Optional[str] = None,
    dynamic: bool = False,
) -> str:
    """
    Constrói BR Code completo e válido (com CRC).
    Retorna a string final (com CRC) pronta para gerar QR.
    """
    if not chave_pix:
        raise ValueError("chave_pix é obrigatório")
    if valor is not None and valor < 0:
        raise ValueError("valor não pode ser negativo")

    parts = []

    # 00 - Payload Format Indicator
    parts.append(_emv_field_bytes("00", "01"))
    # 01 - Point of initiation
    parts.append(_emv_field_bytes("01", "12" if dynamic else "11"))

    # 26 - Merchant Account Information (subfields)
    # subfield 00 = GUI (BR.GOV.BCB.PIX)
    mai = []
    mai.append(_emv_field_bytes("00", "BR.GOV.BCB.PIX"))
    # subfield 01 = chave PIX
    mai.append(_emv_field_bytes("01", chave_pix))
    # opcional: subfield 02 = description (por ex. referencia humana)
    if description:
        mai.append(_emv_field_bytes("02", description))
    mai_concat = b"".join(mai)
    parts.append(f"26{len(mai_concat):02d}".encode("utf-8") + mai_concat)

    # 52 Merchant Category Code
    parts.append(_emv_field_bytes("52", "0000"))
    # 53 Currency
    parts.append(_emv_field_bytes("53", "986"))
    # 54 Amount (opcional) - formato: no símbolo, com ponto, ex: 10.00
    if valor is not None:
        amount_str = f"{valor:.2f}"
        parts.append(_emv_field_bytes("54", amount_str))

    # 58 Country
    parts.append(_emv_field_bytes("58", "BR"))
    # 59 Merchant name (<=25 bytes) - truncar por bytes se necessário
    name_bytes = merchant_name.encode("utf-8")[:25]
    parts.append(f"59{len(name_bytes):02d}".encode("utf-8") + name_bytes)
    # 60 Merchant city (<=15 bytes)
    city_bytes = merchant_city.encode("utf-8")[:15]
    parts.append(f"60{len(city_bytes):02d}".encode("utf-8") + city_bytes)

    # 62 - Additional Data Field Template (txid subfield 05)
    tx = txid if txid is not None else ""
    sub_62 = _emv_field_bytes("05", tx)
    parts.append(f"62{len(sub_62):02d}".encode("utf-8") + sub_62)

    # montando tudo em bytes e calculando CRC sobre bytes + "6304"
    payload_bytes_no_crc = b"".join(parts) + b"6304"
    crc = crc16(payload_bytes_no_crc)
    full = payload_bytes_no_crc + crc.encode("utf-8")
    return full.decode("utf-8")


def generate_pix_qrcode(chave_pix: str, merchant_name: str, merchant_city: str,
                        valor: Optional[float] = None, txid: Optional[str] = None,
                        description: Optional[str] = None, output_path="qrcode_pix.png") -> str:
    import qrcode

    payload = build_pix_payload(
        chave_pix=chave_pix,
        merchant_name=merchant_name,
        merchant_city=merchant_city,
        valor=valor,
        txid=txid,
        description=description
    )
    # sanity check: recalcula CRC e compara
    # recalcula CRC sobre payload até '6304'
    idx = payload.rfind("63")
    if idx == -1:
        raise RuntimeError("Payload mal formado (sem 63 CRC).")
    without_crc = payload[:idx] + "6304"
    check_crc = crc16(without_crc.encode("utf-8"))
    given_crc = payload[idx+4: idx+8] if len(payload) >= idx+8 else None
    if check_crc != given_crc:
        raise RuntimeError(
            f"CRC mismatch: calculado={check_crc} inserido={given_crc}")

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)
    return output_path
