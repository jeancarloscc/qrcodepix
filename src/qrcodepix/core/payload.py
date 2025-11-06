"""Construção do payload PIX (EMV / BR Code).
Responsabilidade única: montar o payload a partir de parâmetros bem validados.
"""
from typing import Optional
from .crc16 import crc16_ccitt
import unicodedata


def _emv_field(tag: str, value: str) -> str:
    length = len(value.encode("utf-8"))
    return f"{tag}{length:02d}{value}"


def _strip_accents_and_upper(value: str) -> str:
    """Remove diacritics and convert to upper-case ASCII-ish characters.

    Keeps basic punctuation and spaces. This reduces the chance of banks
    rejecting the merchant name/city due to unexpected characters.
    """
    if value is None:
        return ""
    # Normalize and remove diacritics
    nfkd = unicodedata.normalize("NFKD", value)
    ascii_only = nfkd.encode("ASCII", "ignore").decode("ASCII")
    # Collapse whitespace and uppercase
    return " ".join(ascii_only.split()).upper()


def _truncate_by_bytes(value: str, max_bytes: int) -> str:
    """Truncate a string so its UTF-8 encoding is at most max_bytes long.

    Prevents splitting multi-byte characters.
    """
    if value is None:
        return ""
    encoded = b""
    out_chars = []
    for ch in value:
        ch_enc = ch.encode("utf-8")
        if len(encoded) + len(ch_enc) > max_bytes:
            break
        encoded += ch_enc
        out_chars.append(ch)
    return "".join(out_chars)


def _normalize_amount(amount: Optional[str]) -> Optional[str]:
    """Normaliza o valor monetário para ter sempre 2 casas decimais."""
    if amount is None:
        return None
    try:
        # Remove qualquer caractere não numérico exceto ponto
        clean = ''.join(c for c in amount if c.isdigit() or c == '.')
        # Converte para float e formata com 2 casas decimais
        return f"{float(clean):.2f}"
    except ValueError:
        raise ValueError("amount deve ser um valor numérico válido")


def _normalize_pix_key(pix_key: str) -> str:
    """Normaliza a chave PIX removendo espaços e caracteres especiais."""
    if not pix_key:
        raise ValueError("pix_key é obrigatório")

    # Remove espaços e converte para minúsculas
    clean_key = ''.join(pix_key.split()).lower()

    # Se for telefone, garante formato +55
    if clean_key.isdigit() and len(clean_key) == 11:
        return f"+55{clean_key}"

    # Se for CPF/CNPJ, remove pontuação
    if any(c in clean_key for c in '.-/'):
        nums = ''.join(c for c in clean_key if c.isdigit())
        if len(nums) in (11, 14):  # CPF ou CNPJ
            return nums

    return clean_key


def build_pix_payload(
    pix_key: str,
    merchant_name: str,
    merchant_city: str,
    amount: Optional[str] = None,
    txid: Optional[str] = None,
    description: Optional[str] = None,
    dynamic: bool = False,
) -> str:
    """Retorna o BR Code completo (string) pronto para gerar QR.

    - pix_key: chave PIX (email/phone/CPF/EVP)
    - merchant_name: até 25 bytes UTF-8 (será truncado)
    - merchant_city: até 15 bytes UTF-8 (será truncado)
    - amount: string no formato '10.00' ou None
    - txid: até 25 chars; se None => txid vazio
    - description: texto opcional (será normalizado)
    - dynamic: True => Point of Initiation Method = '12' (dinâmico)
    """
    # Validações e normalizações
    pix_key = _normalize_pix_key(pix_key)
    amount = _normalize_amount(amount)

    payload = []
    payload.append(_emv_field("00", "01"))
    payload.append(_emv_field("01", "12" if dynamic else "11"))

    # Merchant Account Info (26) - GUI e chave PIX
    mai = []
    mai.append(_emv_field("00", "BR.GOV.BCB.PIX"))
    mai.append(_emv_field("01", pix_key))
    if description:
        # Normaliza e trunca a descrição também
        desc_norm = _strip_accents_and_upper(description)
        desc_trunc = _truncate_by_bytes(desc_norm, 50)  # limite arbitrário
        mai.append(_emv_field("02", desc_trunc))
    mai_concat = "".join(mai)
    payload.append(_emv_field("26", mai_concat))

    # Campos obrigatórios na ordem correta
    payload.append(_emv_field("52", "0000"))  # Merchant Category Code
    # Transaction Currency (986 = BRL)
    payload.append(_emv_field("53", "986"))
    if amount is not None:
        payload.append(_emv_field("54", amount))  # Transaction Amount

    payload.append(_emv_field("58", "BR"))
    # Normalize and truncate by BYTES (25 and 15 respectively) to follow EMV rules
    merchant_name_norm = _strip_accents_and_upper(merchant_name)
    merchant_city_norm = _strip_accents_and_upper(merchant_city)
    payload.append(_emv_field(
        "59", _truncate_by_bytes(merchant_name_norm, 25)))
    payload.append(_emv_field(
        "60", _truncate_by_bytes(merchant_city_norm, 15)))

    # Additional Data (62)
    txid_value = txid if txid is not None else ""
    add = _emv_field("05", txid_value)
    payload.append(_emv_field("62", add))

    # CRC
    without_crc = "".join(payload) + "6304"
    crc = crc16_ccitt(without_crc.encode("utf-8"))
    payload.append(_emv_field("63", crc))

    return "".join(payload)
