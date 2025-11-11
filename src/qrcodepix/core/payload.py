from typing import Optional, Tuple
import unicodedata
import re

POLY = 0x1021
INIT = 0xFFFF


def normalize_pix_key(chave: str) -> str:
    """
    Normaliza a chave PIX conforme o tipo detectado.

    Regras por tipo:
    - Email: mantém como está (case-insensitive)
    - Telefone: garante formato +5511999999999 (13 dígitos com +55)
    - CPF/CNPJ: remove formatação (pontos, traços), PRESERVA zeros à esquerda
    - EVP/Aleatória: mantém como está

    Exemplos:
    - Telefone:
      - "11999999999" → "+5511999999999"
      - "5511999999999" → "+5511999999999"
      - "+5511999999999" → "+5511999999999"

    - CPF (PRESERVA zeros à esquerda):
      - "012.345.678-90" → "01234567890" (mantém o 0 inicial)
      - "000.000.001-91" → "00000000191" (mantém todos os zeros)
      - "123.456.789-00" → "12345678900"

    - CNPJ:
      - "00.000.000/0001-00" → "00000000000100" (preserva zeros)
      - "12.345.678/0001-90" → "12345678000190"
    """
    if not chave:
        return chave

    chave = chave.strip()

    # Detectar tipo de chave
    # Se contém @, é email
    if '@' in chave:
        return chave.lower()

    # Remove caracteres não numéricos para análise
    # IMPORTANTE: Usa string, NÃO converte para int, preservando zeros à esquerda
    only_numbers = re.sub(r'[^0-9]', '', chave)

    # Se tem 13 dígitos e começa com 55, é telefone com código do país
    if len(only_numbers) == 13 and only_numbers.startswith('55'):
        return f"+{only_numbers}"

    # Se já tem + no início e 13 dígitos, é telefone
    if chave.startswith('+') and len(only_numbers) == 13:
        return chave

    # Se tem exatamente 11 dígitos
    if len(only_numbers) == 11:
        # Verificar se é telefone ou CPF
        # Telefones no Brasil começam com DDD (2 dígitos) seguido de 9 dígitos
        # DDDs válidos: 11-99 (nenhum DDD começa com 0)
        # CPFs podem começar com 0

        # Se começa com 0, é CPF (DDDs não começam com 0)
        if only_numbers[0] == '0':
            return only_numbers

        # Se a entrada original tinha formatação de CPF (. ou -), é CPF
        if '.' in chave or '-' in chave:
            return only_numbers

        # Se o segundo dígito é 9 (celular), provavelmente é telefone
        # Telefones celulares: (11) 9xxxx-xxxx
        if len(only_numbers) == 11 and only_numbers[2] in ['9', '8', '7']:
            return f"+55{only_numbers}"

        # Caso contrário, assumir CPF para segurança
        return only_numbers

    # Se tem 14 dígitos (CNPJ), retornar sem formatação
    # PRESERVA zeros à esquerda
    if len(only_numbers) == 14:
        return only_numbers

    # Para chaves aleatórias (EVP) ou outros formatos, manter original
    return chave


def normalize_text(text: str) -> str:
    """
    Normaliza texto conforme especificação do Banco Central para PIX.

    Regras aplicadas:
    - Remove acentuação (á→A, ç→C, ã→A, etc.)
    - Remove caracteres especiais
    - Mantém apenas: letras (A-Z), números (0-9) e espaços
    - Converte para MAIÚSCULAS
    - Remove espaços duplicados e espaços nas extremidades

    Exemplos:
    - "São Paulo" → "SAO PAULO"
    - "José da Silva" → "JOSE DA SILVA"
    - "Capitão Poço" → "CAPITAO POCO"
    """
    if not text:
        return ""

    # Normalização NFD (Normalization Form Decomposed)
    # Separa caracteres base dos diacríticos (á = a + ´)
    text_nfd = unicodedata.normalize('NFD', text)

    # Remove diacríticos (mantém apenas caracteres base)
    # Categoria 'Mn' = Mark, Nonspacing (acentos, til, cedilha, etc.)
    text_without_accents = ''.join(
        char for char in text_nfd if unicodedata.category(char) != 'Mn'
    )

    # Remove todos os caracteres que não sejam letras, números ou espaços
    # Conforme especificação do padrão EMV
    text_clean = re.sub(r'[^A-Za-z0-9\s]', '', text_without_accents)

    # Converte para maiúsculas (padrão do PIX)
    text_upper = text_clean.upper()

    # Remove espaços duplicados e espaços nas extremidades
    text_final = ' '.join(text_upper.split())

    return text_final


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
    Constrói BR Code completo e válido (com CRC) conforme Manual do Banco Central.
    Retorna a string final (com CRC) pronta para gerar QR.

    Especificações:
    - Payload Format: EMV QRCPS Merchant Presented Mode
    - Versão: 01
    - Caracteres permitidos: UTF-8 sem acentos (normalizado)
    - Limites: Nome 25 chars, Cidade 15 chars, TXID 25 chars
    """
    if not chave_pix:
        raise ValueError("chave_pix é obrigatório")
    if not merchant_name or not merchant_city:
        raise ValueError("merchant_name e merchant_city são obrigatórios")
    if valor is not None and valor <= 0:
        raise ValueError("valor deve ser positivo")
    if txid and len(txid) > 25:
        raise ValueError("txid deve ter no máximo 25 caracteres")

    # Normalizar a chave PIX
    chave_pix_normalizada = normalize_pix_key(chave_pix)

    parts = []

    # 00 - Payload Format Indicator (obrigatório, fixo "01")
    parts.append(_emv_field_bytes("00", "01"))

    # 01 - Point of Initiation Method
    # "11" = QR estático (pode ser reutilizado)
    # "12" = QR dinâmico (uso único)
    parts.append(_emv_field_bytes("01", "12" if dynamic else "11"))

    # 26 - Merchant Account Information (obrigatório)
    # GUI obrigatório: BR.GOV.BCB.PIX
    mai = []
    mai.append(_emv_field_bytes("00", "BR.GOV.BCB.PIX"))

    # subfield 01 = chave PIX (obrigatório)
    # Chave normalizada (telefone com +55, CPF/CNPJ sem formatação, etc.)
    mai.append(_emv_field_bytes("01", chave_pix_normalizada))

    # subfield 02 = Informação Adicional/Descrição (opcional, máx 72 chars)
    if description:
        # Normalizar e limitar descrição
        normalized_desc = normalize_text(description)[:72]
        if normalized_desc:
            mai.append(_emv_field_bytes("02", normalized_desc))

    mai_concat = b"".join(mai)
    parts.append(f"26{len(mai_concat):02d}".encode("utf-8") + mai_concat)

    # 52 - Merchant Category Code (obrigatório)
    # "0000" = não especificado
    parts.append(_emv_field_bytes("52", "0000"))

    # 53 - Transaction Currency (obrigatório)
    # "986" = BRL (Real brasileiro) conforme ISO 4217
    parts.append(_emv_field_bytes("53", "986"))

    # 54 - Transaction Amount (condicional)
    # Formato: sem símbolo, ponto como separador decimal, ex: "10.00"
    # Obrigatório se Point of Initiation = "12" (dinâmico)
    if valor is not None:
        amount_str = f"{valor:.2f}"
        parts.append(_emv_field_bytes("54", amount_str))

    # 58 - Country Code (obrigatório)
    # "BR" = Brasil conforme ISO 3166-1 alpha 2
    parts.append(_emv_field_bytes("58", "BR"))

    # 59 - Merchant Name (obrigatório, máx 25 caracteres)
    # Deve ser normalizado (sem acentos, maiúsculas)
    normalized_name = normalize_text(merchant_name)
    if len(normalized_name) > 25:
        normalized_name = normalized_name[:25]
    if not normalized_name:
        raise ValueError(
            "merchant_name não pode estar vazio após normalização")
    parts.append(_emv_field_bytes("59", normalized_name))

    # 60 - Merchant City (obrigatório, máx 15 caracteres)
    # Deve ser normalizado (sem acentos, maiúsculas)
    normalized_city = normalize_text(merchant_city)
    if len(normalized_city) > 15:
        normalized_city = normalized_city[:15]
    if not normalized_city:
        raise ValueError(
            "merchant_city não pode estar vazio após normalização")
    parts.append(_emv_field_bytes("60", normalized_city))

    # 62 - Additional Data Field Template (condicional)
    # subfield 05 = Reference Label / TXID (identificador da transação)
    # Máximo 25 caracteres alfanuméricos
    if txid:
        # Normalizar TXID para garantir apenas caracteres válidos
        normalized_txid = normalize_text(txid)[:25]
        if normalized_txid:
            sub_62 = _emv_field_bytes("05", normalized_txid)
            parts.append(f"62{len(sub_62):02d}".encode("utf-8") + sub_62)

    # 63 - CRC16 (obrigatório, sempre o último campo)
    # Formato: "6304" + 4 dígitos hexadecimais
    # CRC calculado sobre todo o payload incluindo "6304"
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
