from typing import Literal, Optional
import unicodedata
import re

from .crc16 import crc16_ccitt as crc16

TipoChave = Literal["email", "telefone", "documento", "evp"]


def _validar_digitos_verificadores(numeros: str, pesos_dv1: list, pesos_dv2: list) -> bool:
    """Valida os dois dígitos verificadores de CPF/CNPJ pelo algoritmo módulo 11."""
    def _dv(digits: str, pesos: list) -> int:
        soma = sum(int(d) * p for d, p in zip(digits, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    dv1 = _dv(numeros[:len(pesos_dv1)], pesos_dv1)
    if dv1 != int(numeros[len(pesos_dv1)]):
        return False
    dv2 = _dv(numeros[:len(pesos_dv2)], pesos_dv2)
    return dv2 == int(numeros[len(pesos_dv2)])


def validar_cpf(cpf: str) -> bool:
    """Valida CPF (formatado ou não) checando os dígitos verificadores (módulo 11)."""
    numeros = re.sub(r'[^0-9]', '', cpf)
    if len(numeros) != 11 or numeros == numeros[0] * 11:
        return False
    return _validar_digitos_verificadores(
        numeros, pesos_dv1=[10, 9, 8, 7, 6, 5, 4, 3, 2], pesos_dv2=[11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
    )


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ (formatado ou não) checando os dígitos verificadores (módulo 11)."""
    numeros = re.sub(r'[^0-9]', '', cnpj)
    if len(numeros) != 14 or numeros == numeros[0] * 14:
        return False
    pesos_dv1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos_dv2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    return _validar_digitos_verificadores(numeros, pesos_dv1=pesos_dv1, pesos_dv2=pesos_dv2)


def normalize_pix_key(chave: str, tipo_chave: Optional[TipoChave] = None) -> str:
    """
    Normaliza a chave PIX.

    Se `tipo_chave` for informado, ele é respeitado integralmente (sem heurística):
    - "email": minúsculas
    - "telefone": normaliza para +55DDDNNNNNNNNN
    - "documento": remove formatação, valida dígito verificador de CPF (11) ou CNPJ (14)
    - "evp": mantém como está

    Se `tipo_chave` for None, tenta autodetectar SOMENTE nos casos não ambíguos
    (email, telefone com +55/13 dígitos, CNPJ com 14 dígitos, CPF formatado ou
    começando com 0). Uma chave numérica de 11 dígitos sem formatação e sem
    prefixo de país é inerentemente ambígua entre telefone e CPF — nesse caso
    é levantado ValueError pedindo que `tipo_chave` seja especificado, em vez
    de adivinhar (adivinhar errado gera um QR PIX apontando para a chave errada).
    """
    if not chave:
        return chave

    chave = chave.strip()
    only_numbers = re.sub(r'[^0-9]', '', chave)

    if tipo_chave == "email":
        return chave.lower()

    if tipo_chave == "telefone":
        if len(only_numbers) == 13 and only_numbers.startswith('55'):
            return f"+{only_numbers}"
        if len(only_numbers) == 11:
            return f"+55{only_numbers}"
        raise ValueError(
            f"Telefone inválido: '{chave}'. Use formato +5511999999999 ou 11999999999.")

    if tipo_chave == "documento":
        if len(only_numbers) == 11 and not validar_cpf(only_numbers):
            raise ValueError(f"CPF inválido (dígito verificador incorreto): '{chave}'.")
        if len(only_numbers) == 14 and not validar_cnpj(only_numbers):
            raise ValueError(f"CNPJ inválido (dígito verificador incorreto): '{chave}'.")
        if len(only_numbers) not in (11, 14):
            raise ValueError(f"Documento inválido: '{chave}'. CPF deve ter 11 dígitos e CNPJ 14.")
        return only_numbers

    if tipo_chave == "evp":
        return chave

    # --- Autodetecção (apenas casos não ambíguos) ---

    if '@' in chave:
        return chave.lower()

    if len(only_numbers) == 13 and only_numbers.startswith('55'):
        return f"+{only_numbers}"

    if chave.startswith('+') and len(only_numbers) == 13:
        return chave

    if len(only_numbers) == 11:
        # DDDs nunca começam com 0 → inequivocamente CPF
        if only_numbers[0] == '0':
            return only_numbers

        # Formatação de CPF (. ou -) é um sinal forte e inequívoco
        if '.' in chave or '-' in chave:
            return only_numbers

        # 11 dígitos, sem formatação, sem prefixo de país: ambíguo entre
        # telefone celular (DDD+9+8 dígitos) e CPF. Não adivinhar.
        raise ValueError(
            f"Chave '{chave}' é ambígua entre telefone e CPF (11 dígitos sem "
            "formatação). Especifique tipo_chave='telefone' ou tipo_chave='documento'."
        )

    if len(only_numbers) == 14:
        return only_numbers

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
    tipo_chave: Optional[TipoChave] = None,
) -> str:
    """
    Constrói BR Code completo e válido (com CRC) conforme Manual do Banco Central.
    Retorna a string final (com CRC) pronta para gerar QR.

    Especificações:
    - Payload Format: EMV QRCPS Merchant Presented Mode
    - Versão: 01
    - Caracteres permitidos: UTF-8 sem acentos (normalizado)
    - Limites: Nome 25 chars, Cidade 15 chars, TXID 25 chars

    `tipo_chave` ("email"/"telefone"/"documento"/"evp") evita autodetecção
    ambígua da chave — ver `normalize_pix_key`.
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
    chave_pix_normalizada = normalize_pix_key(chave_pix, tipo_chave=tipo_chave)

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

    # 62 - Additional Data Field Template (obrigatório pelo Manual BR Code do BCB)
    # subfield 05 = Reference Label / TXID (identificador da transação)
    # Máximo 25 caracteres alfanuméricos. Quando não há txid específico,
    # o Manual do BCB exige o valor "***" — omitir o campo inteiro é
    # rejeitado como "parâmetros inválidos" por bancos que validam
    # estritamente contra o manual (ex: Banco do Brasil).
    normalized_txid = normalize_text(txid)[:25] if txid else ""
    if not normalized_txid:
        normalized_txid = "***"
    sub_62 = _emv_field_bytes("05", normalized_txid)
    parts.append(f"62{len(sub_62):02d}".encode("utf-8") + sub_62)

    # 63 - CRC16 (obrigatório, sempre o último campo)
    # Formato: "6304" + 4 dígitos hexadecimais
    # CRC calculado sobre todo o payload incluindo "6304"
    payload_bytes_no_crc = b"".join(parts) + b"6304"
    crc = crc16(payload_bytes_no_crc)
    full = payload_bytes_no_crc + crc.encode("utf-8")

    return full.decode("utf-8")
