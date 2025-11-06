"""
Interface web para geração de QR Codes PIX usando Streamlit.
"""
import re
import io
import zipfile
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


def generate_qr(payload: str) -> Tuple[Path, Path]:
    """Gera arquivos QR code PNG e SVG."""
    with TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "pix_qr"
        try:
            png_path, svg_path = save_qr_files(
                payload, filename_base=str(base))

            # Converter os caminhos retornados para objetos Path
            png_path = Path(png_path)
            svg_path = Path(svg_path)

            # Copiar arquivos para um local persistente
            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            persistent_png = output_dir / png_path.name
            persistent_svg = output_dir / svg_path.name
            png_path.replace(persistent_png)
            svg_path.replace(persistent_svg)

            return persistent_png, persistent_svg
        except Exception as e:
            st.error(f"Erro ao gerar QR: {str(e)}")
            st.stop()


def show_qr_downloads(png_path: Path, svg_path: Path) -> None:
    """Exibe o QR code e cria botões de download."""
    try:
        from PIL import Image
        img = Image.open(png_path)
        st.image(img, caption="QR PIX (PNG)", use_container_width=False)
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


def process_form(key: str, name: str, city: str, amount: str, txid: str, desc: str) -> None:
    """Processa o formulário e gera o QR code."""
    validate_form_input(key, name, city, amount)

    try:
        amount_norm = float(amount.replace(',', '.')) if amount else None

        payload = build_pix_payload(
            chave_pix=key,
            merchant_name=name,
            merchant_city=city,
            valor=amount_norm,
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
        png_path, svg_path = generate_qr(payload)
        show_qr_downloads(png_path, svg_path)
        st.success("QR Code gerado com sucesso!")


def main():
    """Função principal da aplicação."""
    st.set_page_config(page_title="Gerador PIX QR", layout="centered")
    st.title("Gerador PIX QR (PNG + SVG)")

    with st.form("pix_form"):
        key = st.text_input("Chave PIX (email/telefone/CPF/EVP)", "")
        name = st.text_input("Nome do recebedor (máx 25)", "")
        city = st.text_input("Cidade (máx 15)", "")
        amount = st.text_input("Valor (opcional, ex: 10.00)", "")
        txid = st.text_input("TXID (opcional)", "")
        desc = st.text_input("Descrição (opcional)", "")
        submitted = st.form_submit_button("Gerar")

    if submitted:
        process_form(key, name, city, amount, txid, desc)


if __name__ == "__main__":
    main()
