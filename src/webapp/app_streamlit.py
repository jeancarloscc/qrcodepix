"""
Interface web para geração de QR Codes PIX usando Streamlit.
"""
import re
import io
import zipfile
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Tuple

import streamlit as st
from qrcodepix.core.payload import build_pix_payload
from qrcodepix.generator.qr import save_qr_files


def validate_cpf(cpf: str) -> bool:
    """Valida o formato do CPF."""
    cpf = re.sub(r'[^0-9]', '', cpf)
    return len(cpf) == 11


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


def make_zip_bytes(png_path: Path, svg_path: Path) -> bytes:
    """Cria um arquivo ZIP com PNG e SVG."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(png_path, arcname=png_path.name)
        zf.write(svg_path, arcname=svg_path.name)
    buf.seek(0)
    return buf.read()


def generate_qr(payload: str, scale: int = 8) -> Tuple[Path, Path]:
    """Gera arquivos QR code PNG e SVG."""
    with TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "pix_qr"
        try:
            png_path, svg_path = save_qr_files(
                payload, filename_base=str(base), scale=scale)

            # Converter os caminhos retornados para objetos Path
            png_path = Path(png_path)
            svg_path = Path(svg_path)

            # Copiar arquivos para um local persistente
            output_dir = Path("output").resolve()
            output_dir.mkdir(exist_ok=True)
            persistent_png = output_dir / png_path.name
            persistent_svg = output_dir / svg_path.name

            # Usar shutil.copy2 para copiar arquivos entre diferentes filesystems
            shutil.copy2(str(png_path), str(persistent_png))
            shutil.copy2(str(svg_path), str(persistent_svg))

            return persistent_png, persistent_svg
        except Exception as e:
            st.error(f"Erro ao gerar QR: {str(e)}")
            st.stop()


def show_qr_downloads(png_path: Path, svg_path: Path) -> None:
    """Exibe o QR code e cria botões de download."""
    try:
        from PIL import Image
        img = Image.open(png_path)
        st.image(img, caption="QR PIX (PNG)", width='stretch')
    except ImportError:
        st.info("PNG gerado — não foi possível exibir (Pillow ausente).")

    with open(png_path, "rb") as f:
        st.download_button("Baixar PNG", data=f.read(),
                           file_name=png_path.name, mime="image/png")

    with open(svg_path, "rb") as f:
        st.download_button("Baixar SVG", data=f.read(),
                           file_name=svg_path.name, mime="image/svg+xml")

    zip_bytes = make_zip_bytes(png_path, svg_path)
    st.download_button("Baixar ZIP (PNG + SVG)", data=zip_bytes,
                       file_name="pix_qr_files.zip", mime="application/zip")


def validate_form_input(key: str, name: str, city: str, amount: Optional[str]) -> None:
    """Valida todos os campos do formulário."""
    if not key or not name or not city:
        st.error("Campos obrigatórios: chave, nome e cidade.")
        st.stop()

    # Validar chave PIX
    if '@' in key:
        if not validate_email(key):
            st.error("Formato de email inválido")
            st.stop()
    elif key.isdigit() or '+' in key:
        if not validate_phone(key):
            st.error(
                "Formato de telefone inválido. Use: +5511999999999 ou 11999999999")
            st.stop()
    elif re.sub(r'[^0-9]', '', key).isdigit():
        if not validate_cpf(key):
            st.error("Formato de CPF inválido")
            st.stop()

    if amount and not validate_amount(amount):
        st.error("Valor inválido. Use formato: 10.00")
        st.stop()


def process_form(key: str, name: str, city: str, amount: str, txid: str, desc: str, scale: int) -> None:
    """Processa o formulário e gera o QR code."""
    validate_form_input(key, name, city, amount)

    try:
        amount_norm = float(amount.replace(',', '.')) if amount else None

        payload = build_pix_payload(
            chave_pix=key,
            merchant_name=name,
            merchant_city=city,
            valor=amount_norm or None,
            txid=txid or None,
            description=desc or None,
        )
    except ValueError as e:
        st.error(f"Erro de validação: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"Erro ao gerar payload: {str(e)}")
        st.stop()

    with st.spinner("Gerando QR..."):
        png_path, svg_path = generate_qr(payload, scale=scale)
        show_qr_downloads(png_path, svg_path)
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
            "placeholder": "12345678900",
            "example": "🆔 **Exemplos CPF:** 123.456.789-00 ou 12345678900\n\n**Exemplos CNPJ:** 12.345.678/0001-90 ou 12345678000190",
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
        process_form(key, name, city, amount, txid, desc, scale)


if __name__ == "__main__":
    main()
