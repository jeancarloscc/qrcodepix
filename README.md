# PIX QR Generator

![GitHub repo size](https://img.shields.io/github/repo-size/jeancarloscc/qrcodepix?style=for-the-badge)
![GitHub language count](https://img.shields.io/github/languages/count/jeancarloscc/qrcodepix?style=for-the-badge)
![GitHub forks](https://img.shields.io/github/forks/jeancarloscc/qrcodepix?style=for-the-badge)
![GitHub open issues](https://img.shields.io/github/issues/jeancarloscc/qrcodepix?style=for-the-badge)
![GitHub pull requests](https://img.shields.io/github/issues-pr/jeancarloscc/qrcodepix?style=for-the-badge)

<img src="docs/example.png" alt="Exemplo de QR Code gerado" width="400">

> Gere QR Codes PIX prontos para uso em segundos — direto do seu código ou pelo navegador.
> Uma ferramenta prática, moderna e gratuita para quem deseja automatizar pagamentos, criar integrações financeiras ou oferecer soluções de cobrança digital com facilidade.
> Ideal para desenvolvedores, empreendedores e equipes que buscam agilidade sem depender de plataformas externas.

---

### 🚧 Ajustes e melhorias

O projeto ainda está em desenvolvimento. As próximas atualizações incluirão:

- [x] Geração de QR Code em PNG e SVG  
- [x] CLI (linha de comando) funcional  
- [x] Versão web em Flask  
- [ ] Integração com banco de dados para histórico de pagamentos  
- [ ] Interface web aprimorada com Bootstrap  

---

## 💻 Pré-requisitos

Antes de começar, verifique se você possui:

- Python **3.9+** instalado  
- `pip` atualizado  
- Sistema operacional: **Windows**, **Linux** ou **macOS**

---

## 🚀 Instalando PIX QR Generator

Clone o repositório e instale as dependências:

```bash
git clone https://github.com/jeancarloscc/qrcodepix.git
cd qrcodepix
pip install -r requirements.txt
````

---

## ☕ Usando o projeto

### 🔹 Linha de comando (CLI)

Gerar um QR Code com valor fixo:

```bash
python -m pix_qr.cli.main --key seu_email@exemplo.com --name "NOME" --city "SAO PAULO" --amount 10.00 --txid ABC123 --out minha_saida
```

Gerar um QR Code **sem valor definido** (opcional):

```bash
python -m pix_qr.cli.main --key seu_email@exemplo.com --name "NOME" --city "SAO PAULO" --txid LIVRE --out pix_sem_valor
```

Os arquivos serão salvos em:

```
./minha_saida.png
./minha_saida.svg
```

### 🔹 Interface Web (Flask)

Execute o servidor local:

```bash
python -m pix_qr.webapp.app
```

Acesse no navegador:
👉 [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 📫 Contribuindo

Para contribuir com **PIX QR Generator**:

1. Faça um fork do repositório
2. Crie uma branch:

   ```bash
   git checkout -b feature/nova-funcionalidade
   ```
3. Faça suas alterações e commit:

   ```bash
   git commit -m "Adiciona nova funcionalidade"
   ```
4. Envie para o repositório remoto:

   ```bash
   git push origin feature/nova-funcionalidade
   ```
5. Abra um **Pull Request**.

---

## 🤝 Colaboradores

Agradecimentos aos desenvolvedores que contribuíram com este projeto:

<table>
  <tr>
    <td align="center">
      <a href="#" title="Jean - Criador do projeto">
        <img src="https://avatars.githubusercontent.com/u/1" width="100px;" alt="Foto do Jean"/><br>
        <sub><b>Jean</b></sub>
      </a>
    </td>
  </tr>
</table>

---

## 😄 Seja um dos contribuidores

Quer fazer parte desse projeto?
Leia [CONTRIBUTING.md](CONTRIBUTING.md) e veja como contribuir.

---

## 📝 Licença

Este projeto está sob a licença MIT.
Consulte o arquivo [LICENSE](LICENSE.md) para mais detalhes.

