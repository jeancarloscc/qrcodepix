"""
Interface web para geração de QR Codes PIX usando Streamlit.
"""
import io
import re
import zipfile
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
from qrcodepix.core.payload import build_pix_payload, validar_cpf, validar_cnpj
from qrcodepix.generator.qr import save_qr_files

KEY_TYPE_TO_TIPO_CHAVE = {
    "Email": "email",
    "Telefone": "telefone",
    "CPF/CNPJ": "documento",
    "Chave Aleatória (EVP)": "evp",
}


def validate_documento(documento: str) -> bool:
    """Valida CPF (11 dígitos) ou CNPJ (14 dígitos) pelo dígito verificador."""
    numeros = re.sub(r'[^0-9]', '', documento)
    if len(numeros) == 11:
        return validar_cpf(numeros)
    if len(numeros) == 14:
        return validar_cnpj(numeros)
    return False


def validate_phone(phone: str) -> bool:
    """Valida o formato do telefone."""
    phone = re.sub(r'[^0-9+]', '', phone)
    return len(phone) >= 11 and len(phone) <= 14


def validate_email(email: str) -> bool:
    """Valida o formato do email."""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def validate_amount(amount: str) -> bool:
    """Valida o formato do valor monetário."""
    if not amount:
        return True
    try:
        value = float(amount.replace(',', '.'))
        return value > 0 and len(str(value).split('.')[-1]) <= 2
    except ValueError:
        return False


def make_zip_bytes(png_bytes: bytes, svg_bytes: bytes) -> bytes:
    """Cria um arquivo ZIP com PNG e SVG em memória."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("pix_qr.png", png_bytes)
        zf.writestr("pix_qr.svg", svg_bytes)
    buf.seek(0)
    return buf.read()


def generate_qr(payload: str, scale: int = 8) -> Tuple[bytes, bytes]:
    """Gera o QR code em um diretório temporário e retorna os bytes de PNG e SVG.

    Não persiste nada fora do diretório temporário: um servidor Streamlit
    compartilhado não deve acumular arquivos com chaves PIX de outros usuários
    em um diretório de saída permanente.
    """
    with TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "pix_qr"
        try:
            png_path, svg_path = save_qr_files(
                payload, filename_base=str(base), scale=scale)
            png_bytes = Path(png_path).read_bytes()
            svg_bytes = Path(svg_path).read_bytes()
            return png_bytes, svg_bytes
        except Exception as e:
            st.error(f"Erro ao gerar QR: {str(e)}")
            st.stop()


def show_qr_downloads(png_bytes: bytes, svg_bytes: bytes) -> None:
    """Exibe o QR code e cria botões de download."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(png_bytes))
        st.image(img, caption="QR PIX (PNG)", width='stretch')
    except ImportError:
        st.info("PNG gerado — não foi possível exibir (Pillow ausente).")

    st.download_button("Baixar PNG", data=png_bytes,
                       file_name="pix_qr.png", mime="image/png")

    st.download_button("Baixar SVG", data=svg_bytes,
                       file_name="pix_qr.svg", mime="image/svg+xml")

    zip_bytes = make_zip_bytes(png_bytes, svg_bytes)
    st.download_button("Baixar ZIP (PNG + SVG)", data=zip_bytes,
                       file_name="pix_qr_files.zip", mime="application/zip")


def validate_form_input(key_type: str, key: str, name: str, city: str, amount: Optional[str]) -> None:
    """Valida todos os campos do formulário de acordo com o tipo de chave selecionado."""
    if not key or not name or not city:
        st.error("Campos obrigatórios: chave, nome e cidade.")
        st.stop()

    if key_type == "Email":
        if not validate_email(key):
            st.error("Formato de email inválido")
            st.stop()
    elif key_type == "Telefone":
        if not validate_phone(key):
            st.error(
                "Formato de telefone inválido. Use: +5511999999999 ou 11999999999")
            st.stop()
    elif key_type == "CPF/CNPJ":
        if not validate_documento(key):
            st.error("CPF/CNPJ inválido (dígito verificador incorreto)")
            st.stop()

    if amount and not validate_amount(amount):
        st.error("Valor inválido. Use formato: 10.00")
        st.stop()


def process_form(key_type: str, key: str, name: str, city: str, amount: str,
                 txid: str, desc: str, scale: int) -> None:
    """Processa o formulário e gera o QR code."""
    validate_form_input(key_type, key, name, city, amount)

    try:
        amount_norm = float(amount.replace(',', '.')) if amount else None

        payload = build_pix_payload(
            chave_pix=key,
            merchant_name=name,
            merchant_city=city,
            valor=amount_norm or None,
            txid=txid or None,
            description=desc or None,
            tipo_chave=KEY_TYPE_TO_TIPO_CHAVE.get(key_type),
        )
    except ValueError as e:
        st.error(f"Erro de validação: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao gerar payload: {str(e)}")
        st.stop()

    with st.spinner("Gerando QR..."):
        png_bytes, svg_bytes = generate_qr(payload, scale=scale)
        show_qr_downloads(png_bytes, svg_bytes)
        st.success("QR Code gerado com sucesso!")


def main():
    """Função principal da aplicação."""
    st.set_page_config(page_title="Gerador PIX QR", layout="centered")
    st.title("Gerador PIX QR (PNG + SVG)")

    # Seletor de tipo de chave PIX (fora do formulário para atualização dinâmica)
    key_type = st.selectbox(
        "Tipo de Chave PIX",
        options=["Email", "Telefone", "CPF/CNPJ", "Chave Aleatória (EVP)"],
        index=0,
        help="Selecione o tipo da sua chave PIX"
    )

    # Exemplos e placeholders baseados no tipo de chave
    examples_map = {
        "Email": {
            "placeholder": "seuemail@exemplo.com",
            "example": "📧 **Exemplo:** joao.silva@gmail.com, maria@empresa.com.br",
            "help": "Digite o endereço de email cadastrado como chave PIX"
        },
        "Telefone": {
            "placeholder": "+5511999999999",
            "example": "📱 **Exemplos:** +5511987654321, +5521912345678, 11987654321",
            "help": "Digite o telefone com código do país (+55) ou apenas com DDD"
        },
        "CPF/CNPJ": {
            "placeholder": "12345678909",
            "example": "🆔 **Exemplos CPF:** 123.456.789-09 ou 12345678909\n\n**Exemplos CNPJ:** 11.222.333/0001-81 ou 11222333000181",
            "help": "Digite o CPF ou CNPJ com ou sem formatação"
        },
        "Chave Aleatória (EVP)": {
            "placeholder": "123e4567-e89b-12d3-a456-426614174000",
            "example": "🔑 **Exemplo:** 123e4567-e89b-12d3-a456-426614174000\n\nChave aleatória gerada pelo seu banco no formato UUID",
            "help": "Cole a chave aleatória (EVP) fornecida pelo seu banco"
        }
    }

    # Mostrar exemplo do tipo de chave selecionado
    current_example = examples_map.get(key_type, {})
    if current_example.get("example"):
        st.info(current_example["example"])

    # Formulário com os campos de entrada
    with st.form("pix_form"):
        # Campo de entrada da chave
        key = st.text_input(
            "Chave PIX",
            placeholder=current_example.get("placeholder", ""),
            help=current_example.get("help", "Informe sua chave PIX")
        )

        name = st.text_input("Nome do recebedor (máx 25)",
                             placeholder="João Silva")
        city = st.text_input("Cidade (máx 15)", placeholder="São Paulo")
        amount = st.text_input(
            "Valor (opcional, ex: 10.00)", placeholder="10.00")
        txid = st.text_input(
            "Identificador - TXID (opcional)", placeholder="REF123456")
        desc = st.text_input("Descrição (opcional)",
                             placeholder="Pagamento de serviço")

        # Controle de tamanho do QR Code
        scale = st.slider(
            "Tamanho do QR Code",
            min_value=5,
            max_value=20,
            value=10,
            step=1,
            help="Quanto maior o valor, maior será o QR Code gerado (PNG e SVG)"
        )

        submitted = st.form_submit_button("Gerar QR Code PIX")

    if submitted:
        process_form(key_type, key, name, city, amount, txid, desc, scale)


if __name__ == "__main__":
    main()
