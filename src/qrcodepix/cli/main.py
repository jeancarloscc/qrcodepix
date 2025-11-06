"""CLI mínimo para gerar o QR PIX a partir de parâmetros.
Uso: python -m pix_qr.cli.main --key ... --name ... --city ... [--amount 10.00] [--txid X]
"""
import argparse
from ..core.payload import build_pix_payload
from ..generator.qr import save_qr_files


def parse_args():
    parser = argparse.ArgumentParser(
        description="Gerar QR Code PIX (PNG + SVG)")
    parser.add_argument("--key", required=True,
                        help="Chave PIX (email/telefone/CPF/EVP)")
    parser.add_argument("--name", required=True,
                        help="Nome do recebedor (máx 25)")
    parser.add_argument("--city", required=True,
                        help="Cidade do recebedor (máx 15)")
    parser.add_argument("--amount", required=False, help="Valor, ex: 10.00")
    parser.add_argument("--txid", required=False, help="txid (até 25 chars)")
    parser.add_argument("--desc", required=False, help="Descrição (opcional)")
    parser.add_argument("--out", default="pix_qr",
                        help="Prefixo do arquivo de saída")
    return parser.parse_args()


def main():
    args = parse_args()
    payload = build_pix_payload(
        chave_pix=args.key,
        merchant_name=args.name,
        merchant_city=args.city,
        valor=float(args.amount) if args.amount else None,
        txid=args.txid,
        description=args.desc,
    )
    png, svg = save_qr_files(payload, filename_base=args.out)
    print(f"Arquivos gerados: {png}, {svg}")


if __name__ == "__main__":
    main()
