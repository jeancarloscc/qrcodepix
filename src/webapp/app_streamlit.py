# app_streamlit.py
# Instalar: pip install streamlit segno qrcode[pil,svg] Pillow
# Executar: streamlit run app_streamlit.py

import streamlit as st
from tempfile import TemporaryDirectory
from pathlib import Path
import zipfile
import io

# importe do seu pacote modularizado
from qrcodepix.core.payload import create_pix_payload
from qrcodepix.generator.qr import save_qr_files

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


def make_zip_bytes(png_path: str, svg_path: str, zip_name: str = "pix_qr_files.zip") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(png_path, arcname=Path(png_path).name)
        zf.write(svg_path, arcname=Path(svg_path).name)
    buf.seek(0)
    return buf.read()


if submitted:
    # validação simples
    if not key or not name or not city:
        st.error("Campos obrigatórios: chave, nome e cidade.")
    else:
        try:
            payload = create_pix_payload(
                chave_pix=key,
                merchant_name=name,
                merchant_city=city,
                valor=amount or None,
                txid=txid or None,
                description=desc or None,
            )
        except Exception as e:
            st.error(f"Erro ao construir payload: {e}")
        else:
            with st.spinner("Gerando QR..."):
                with TemporaryDirectory() as tmpdir:
                    base = Path(tmpdir) / "pix_qr"
                    png_path, svg_path = save_qr_files(
                        payload, filename_base=str(base))
                    # mostrar imagem PNG
                    try:
                        from PIL import Image
                        img = Image.open(png_path)
                        st.image(img, caption="QR PIX (PNG)",
                                 use_container_width=False)
                    except Exception:
                        st.info(
                            "PNG gerado — não foi possível exibir (Pillow ausente).")
                    # botão de download do PNG
                    with open(png_path, "rb") as f:
                        st.download_button("Baixar PNG", data=f.read(
                        ), file_name=Path(png_path).name, mime="image/png")
                    # botão de download do SVG
                    with open(svg_path, "rb") as f:
                        st.download_button("Baixar SVG", data=f.read(), file_name=Path(
                            svg_path).name, mime="image/svg+xml")
                    # ZIP com ambos
                    zip_bytes = make_zip_bytes(png_path, svg_path)
                    st.download_button("Baixar ZIP (PNG + SVG)", data=zip_bytes,
                                       file_name="pix_qr_files.zip", mime="application/zip")
            st.success("Pronto.")
