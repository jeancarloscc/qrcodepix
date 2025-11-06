"""
Testes unitários para o gerador de QR Code PIX.
"""
import unittest
from qrcodepix.core.payload import build_pix_payload


class TestPixPayload(unittest.TestCase):
    def test_email_pix_key(self):
        """Testa geração de payload com chave PIX tipo email."""
        payload = build_pix_payload(
            chave_pix="teste@email.com",
            merchant_name="LOJA TESTE",
            merchant_city="SAO PAULO",
            amount="10.00",
        )
        self.assertIn("BR.GOV.BCB.PIX", payload)
        self.assertIn("teste@email.com", payload)
        self.assertIn("LOJA TESTE", payload)
        self.assertIn("SAO PAULO", payload)
        self.assertIn("10.00", payload)

    def test_cpf_pix_key(self):
        """Testa geração de payload com chave PIX tipo CPF."""
        payload = build_pix_payload(
            chave_pix="123.456.789-09",  # Com pontuação
            merchant_name="José da Silva",  # Com acento
            merchant_city="São Paulo",    # Com acento
            amount="15.99",
        )
        self.assertIn("12345678909", payload)  # CPF sem pontuação
        self.assertIn("JOSE DA SILVA", payload)  # Nome sem acento
        self.assertIn("SAO PAULO", payload)     # Cidade sem acento
        self.assertIn("15.99", payload)

    def test_phone_pix_key(self):
        """Testa geração de payload com chave PIX tipo telefone."""
        payload = build_pix_payload(
            chave_pix="11999999999",  # Sem +55
            merchant_name="LOJA & CIA",  # Com &
            merchant_city="RIO DE JANEIRO",
            amount="1500.00",
        )
        self.assertIn("+5511999999999", payload)  # Telefone com +55
        self.assertIn("LOJA & CIA", payload)
        self.assertIn("RIO DE JANEIRO", payload)
        self.assertIn("1500.00", payload)

    def test_invalid_amount(self):
        """Testa validação de valor inválido."""
        with self.assertRaises(ValueError):
            build_pix_payload(
                chave_pix="teste@email.com",
                merchant_name="LOJA TESTE",
                merchant_city="SAO PAULO",
                amount="invalid",
            )

    def test_description_with_special_chars(self):
        """Testa descrição com caracteres especiais."""
        payload = build_pix_payload(
            chave_pix="teste@email.com",
            merchant_name="LOJA TESTE",
            merchant_city="SAO PAULO",
            amount="10.00",
            description="Pagamento nº 123 - Referência",
        )
        self.assertIn("PAGAMENTO N 123 - REFERENCIA", payload.upper())

    def test_long_merchant_name(self):
        """Testa truncamento do nome do merchant."""
        long_name = "NOME MUITO LONGO QUE DEVE SER TRUNCADO"
        payload = build_pix_payload(
            chave_pix="teste@email.com",
            merchant_name=long_name,
            merchant_city="SAO PAULO",
            amount="10.00",
        )
        # 25 + 2 dígitos length
        self.assertLess(len(payload.split("59")[1].split("60")[0]), 27)

    def test_dynamic_pix(self):
        """Testa geração de PIX dinâmico."""
        payload = build_pix_payload(
            chave_pix="teste@email.com",
            merchant_name="LOJA TESTE",
            merchant_city="SAO PAULO",
            amount="10.00",
            dynamic=True,
        )
        # Point of Initiation Method = 12 (dinâmico)
        self.assertIn("0112", payload)


if __name__ == "__main__":
    unittest.main()
