"""CRC-16 para uso no payload EMV/BR Code.
Implementação pequena, pura, com testes fáceis.
"""
from typing import ByteString


POLY = 0x1021
INIT = 0xFFFF


def crc16_ccitt(data: ByteString) -> str:
    """Calcula CRC-16/CCITT (polynomial 0x1021, inicial 0xFFFF).
    Retorna string hex em MAIÚSCULAS com 4 caracteres.
    """
    crc = INIT
    for b in data:
        crc ^= (b << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) & 0xFFFF) ^ POLY
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"
