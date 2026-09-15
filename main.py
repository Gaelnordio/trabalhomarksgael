import sys
import sqlite3
import re
import json
import urllib.request

from PySide6.QtCore import Qt, QRect, QMarginsF
from PySide6.QtGui import QPdfWriter, QPainter, QPageSize, QPageLayout, QFont, QColor, QPen
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QComboBox,
    QFormLayout, QVBoxLayout, QHBoxLayout, QMessageBox, QTableWidget,
    QTableWidgetItem, QFileDialog, QHeaderView
)

BANCO = "cadastros.db"


def criar_banco():
    with sqlite3.connect(BANCO) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, documento TEXT,
            email TEXT, celular TEXT, cep TEXT, logradouro TEXT, numero TEXT,
            complemento TEXT, bairro TEXT, cidade TEXT, estado TEXT)""")


def numeros(texto):
    return re.sub(r"\D", "", texto)


def cpf_valido(cpf):
    cpf = numeros(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (soma * 10 % 11) % 10
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (soma * 10 % 11) % 10
    return cpf[-2:] == f"{d1}{d2}"


def email_valido(email):
    return re.match(r"^[\w.-]+@[\w.-]+\.\w+$", email) is not None


class Janela(QWidget):
    def __init__(self):
        super().__init__()
        self.id_selecionado = None
        self.setWindowTitle("Cadastro de Pessoa - CRUD")
        self.resize(1180, 820)
        self.setObjectName("pagina")
        self.setStyleSheet("""
            QWidget {
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 13px;
                color: #243447;
            }
            QWidget#pagina {
                background-color: #f3f6fb;
            }
            QLabel#titulo {
                color: #173b67;
                font-size: 28px;
                font-weight: 700;
                padding: 4px 0;
            }
            QLabel#subtitulo {
                color: #718096;
                font-size: 13px;
                padding-bottom: 8px;
            }
            QGroupBox {
                background: white;
                border: 1px solid #d9e2ec;
                border-radius: 10px;
                margin-top: 12px;
                padding: 18px 14px 12px 14px;
                font-weight: 700;
                color: #24415f;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 7px;
                background: white;
            }
            QLineEdit, QComboBox {
                background: #fbfdff;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 9px 10px;
                min-height: 18px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #3182ce;
                background: white;
            }
            QPushButton {
                background: #e8eef6;
                color: #294866;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: 600;
            }
            QPushButton:hover { background: #d6e3f2; }
            QPushButton:pressed { background: #bfd2e8; }
            QPushButton#salvar { background: #2563eb; color: white; }
            QPushButton#salvar:hover { background: #1d4ed8; }
            QPushButton#editar { background: #0f766e; color: white; }
            QPushButton#editar:hover { background: #0d625c; }
            QPushButton#excluir { background: #fee2e2; color: #b42318; }
            QPushButton#excluir:hover { background: #fecaca; }
            QPushButton#pdf { background: #7c3aed; color: white; }
            QPushButton#pdf:hover { background: #6d28d9; }
            QTableWidget {
                background: white;
                alternate-background-color: #f7faff;
                border: 1px solid #d9e2ec;
                border-radius: 8px;
                gridline-color: #e5eaf0;
                selection-background-color: #dbeafe;
                selection-color: #173b67;
            }
            QHeaderView::section {
                background: #234e78;
                color: white;
                padding: 10px 6px;
                border: none;
                font-weight: 700;
            }
            QStatusBar { background: #eaf0f7; color: #52606d; }
        """)
        self.criar_campos()
        self.criar_tela()
        self.listar()

    def criar_campos(self):
        self.nome = QLineEdit()
        self.documento = QLineEdit()
        self.email = QLineEdit()
        self.celular = QLineEdit()
        self.cep = QLineEdit()
        self.logradouro = QLineEdit()
        self.numero = QLineEdit()
        self.complemento = QLineEdit()
        self.bairro = QLineEdit()
        self.cidade = QLineEdit()
        self.estado = QComboBox()
        self.estado.addItems(["Selecione", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"])

    def criar_tela(self):
        formulario = QFormLayout()
        formulario.addRow("Nome completo *", self.nome)
        formulario.addRow("CPF *", self.documento)
        formulario.addRow("E-mail *", self.email)
        formulario.addRow("Celular *", self.celular)

        linha_cep = QHBoxLayout()
        linha_cep.addWidget(self.cep)
        botao_cep = QPushButton("Consultar CEP")
        botao_cep.clicked.connect(self.consultar_cep)
        linha_cep.addWidget(botao_cep)
        formulario.addRow("CEP *", linha_cep)

        formulario.addRow("Logradouro *", self.logradouro)
        formulario.addRow("Número *", self.numero)
        formulario.addRow("Complemento", self.complemento)
        formulario.addRow("Bairro *", self.bairro)
        formulario.addRow("Cidade *", self.cidade)
        formulario.addRow("Estado *", self.estado)

        self.botao_salvar = QPushButton("Cadastrar")
        self.botao_editar = QPushButton("Editar selecionado")
        self.botao_excluir = QPushButton("Excluir selecionado")
        self.botao_limpar = QPushButton("Limpar campos")
        self.botao_pdf = QPushButton("Exportar tabela para PDF")
        self.botao_salvar.setObjectName("salvar")
        self.botao_editar.setObjectName("editar")
        self.botao_excluir.setObjectName("excluir")
        self.botao_pdf.setObjectName("pdf")

        self.botao_salvar.clicked.connect(self.salvar)
        self.botao_editar.clicked.connect(self.editar)
        self.botao_excluir.clicked.connect(self.excluir)
        self.botao_limpar.clicked.connect(self.limpar)
        self.botao_pdf.clicked.connect(self.exportar_pdf)

        botoes = QHBoxLayout()
        for botao in [self.botao_salvar, self.botao_editar, self.botao_excluir, self.botao_limpar]:
            botoes.addWidget(botao)

        self.filtro = QLineEdit()
        self.filtro.setPlaceholderText("Digite uma palavra para filtrar a tabela...")
        self.filtro.textChanged.connect(self.listar)

        self.tabela = QTableWidget()
        self.tabela.setColumnCount(6)
        self.tabela.setHorizontalHeaderLabels(["ID", "Nome", "CPF", "E-mail", "Celular", "Cidade"])
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.verticalHeader().setDefaultSectionSize(34)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela.cellClicked.connect(self.selecionar_linha)

        layout = QVBoxLayout()
        titulo = QLabel("Cadastro de Pessoa")
        titulo.setObjectName("titulo")
        subtitulo = QLabel("Gerencie seus cadastros com praticidade")
        subtitulo.setObjectName("subtitulo")
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addLayout(formulario)
        layout.addLayout(botoes)
        layout.addWidget(QLabel("Pesquisar nos cadastros"))
        layout.addWidget(self.filtro)
        layout.addWidget(self.tabela)
        layout.addWidget(self.botao_pdf)
        self.setLayout(layout)

    def consultar_cep(self):
        cep = numeros(self.cep.text())
        if len(cep) != 8:
            QMessageBox.warning(self, "Erro", "Digite um CEP com 8 números.")
            return
        try:
            url = f"https://viacep.com.br/ws/{cep}/json/"
            dados = json.loads(urllib.request.urlopen(url, timeout=10).read())
            if dados.get("erro"):
                QMessageBox.warning(self, "Erro", "CEP não encontrado.")
                return
            self.logradouro.setText(dados.get("logradouro", ""))
            self.bairro.setText(dados.get("bairro", ""))
            self.cidade.setText(dados.get("localidade", ""))
            self.estado.setCurrentText(dados.get("uf", ""))
        except Exception:
            QMessageBox.warning(self, "Erro", "Não foi possível consultar o CEP.")

    def validar(self):
        if not self.nome.text().strip(): return "Digite o nome completo."
        if not cpf_valido(self.documento.text()): return "Digite um CPF válido."
        if not email_valido(self.email.text()): return "Digite um e-mail válido."
        if len(numeros(self.celular.text())) not in (10, 11): return "Celular inválido."
        if len(numeros(self.cep.text())) != 8: return "CEP inválido."
        obrigatorios = [(self.logradouro, "Digite o logradouro."), (self.numero, "Digite o número."), (self.bairro, "Digite o bairro."), (self.cidade, "Digite a cidade.")]
        for campo, mensagem in obrigatorios:
            if not campo.text().strip(): return mensagem
        if self.estado.currentText() == "Selecione": return "Selecione o estado."
        return ""

    def dados(self):
        return (self.nome.text(), self.documento.text(), self.email.text(), self.celular.text(), self.cep.text(), self.logradouro.text(), self.numero.text(), self.complemento.text(), self.bairro.text(), self.cidade.text(), self.estado.currentText())

    # CREATE: insere um novo cadastro; UPDATE: atualiza o cadastro selecionado
    def salvar(self):
        erro = self.validar()
        if erro:
            QMessageBox.warning(self, "Corrija os dados", erro)
            return
        with sqlite3.connect(BANCO) as con:
            if self.id_selecionado is None:
                con.execute("INSERT INTO pessoas (nome,documento,email,celular,cep,logradouro,numero,complemento,bairro,cidade,estado) VALUES (?,?,?,?,?,?,?,?,?,?,?)", self.dados())
                mensagem = "Cadastro realizado com sucesso!"
            else:
                con.execute("UPDATE pessoas SET nome=?,documento=?,email=?,celular=?,cep=?,logradouro=?,numero=?,complemento=?,bairro=?,cidade=?,estado=? WHERE id=?", self.dados() + (self.id_selecionado,))
                mensagem = "Cadastro atualizado com sucesso!"
        QMessageBox.information(self, "Sucesso", mensagem)
        self.limpar()
        self.listar()

    # READ: consulta registros e aplica o filtro digitado
    def listar(self):
        texto = f"%{self.filtro.text()}%"
        with sqlite3.connect(BANCO) as con:
            registros = con.execute("SELECT id,nome,documento,email,celular,cidade FROM pessoas WHERE nome LIKE ? OR documento LIKE ? OR email LIKE ? OR cidade LIKE ? ORDER BY id DESC", (texto, texto, texto, texto)).fetchall()
        self.tabela.setRowCount(len(registros))
        for linha, registro in enumerate(registros):
            for coluna, valor in enumerate(registro):
                self.tabela.setItem(linha, coluna, QTableWidgetItem(str(valor)))

    def selecionar_linha(self, linha, coluna):
        self.id_selecionado = int(self.tabela.item(linha, 0).text())
        with sqlite3.connect(BANCO) as con:
            dados = con.execute("SELECT nome,documento,email,celular,cep,logradouro,numero,complemento,bairro,cidade,estado FROM pessoas WHERE id=?", (self.id_selecionado,)).fetchone()
        campos = [self.nome, self.documento, self.email, self.celular, self.cep, self.logradouro, self.numero, self.complemento, self.bairro, self.cidade]
        for campo, valor in zip(campos, dados[:10]): campo.setText(valor or "")
        self.estado.setCurrentText(dados[10])
        self.botao_salvar.setText("Atualizar cadastro")

    def editar(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.warning(self, "Atenção", "Selecione um cadastro na tabela.")
            return
        self.selecionar_linha(linha, 0)

    # DELETE: remove o cadastro selecionado
    def excluir(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.warning(self, "Atenção", "Selecione um cadastro na tabela.")
            return
        id_registro = int(self.tabela.item(linha, 0).text())
        resposta = QMessageBox.question(self, "Confirmar", "Deseja excluir este cadastro?")
        if resposta == QMessageBox.Yes:
            with sqlite3.connect(BANCO) as con:
                con.execute("DELETE FROM pessoas WHERE id=?", (id_registro,))
            self.limpar()
            self.listar()

    def limpar(self):
        for campo in [self.nome, self.documento, self.email, self.celular, self.cep, self.logradouro, self.numero, self.complemento, self.bairro, self.cidade]: campo.clear()
        self.estado.setCurrentIndex(0)
        self.id_selecionado = None
        self.botao_salvar.setText("Cadastrar")
        self.tabela.clearSelection()

    # Exporta os registros atualmente exibidos na tabela para PDF
    def exportar_pdf(self):
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", "cadastros.pdf", "PDF (*.pdf)")
        if not caminho: return
        pdf = QPdfWriter(caminho)
        pdf.setPageSize(QPageSize(QPageSize.A4))
        pdf.setPageOrientation(QPageLayout.Landscape)
        pdf.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Millimeter)
        painter = QPainter(pdf)
        largura = pdf.width()
        margem = 80
        tabela_largura = largura - (margem * 2)
        alturas = 62
        colunas = ["ID", "Nome", "CPF", "E-mail", "Celular", "Cidade"]
        proporcoes = [0.07, 0.22, 0.17, 0.25, 0.16, 0.13]
        larguras = [int(tabela_largura * p) for p in proporcoes]
        larguras[-1] += tabela_largura - sum(larguras)

        def desenhar_celula(x, y, largura_celula, texto, cabecalho=False):
            painter.setPen(QPen(QColor("#b8c4d1"), 2))
            painter.setBrush(QColor("#234e78") if cabecalho else QColor("#ffffff"))
            painter.drawRect(QRect(x, y, largura_celula, alturas))
            painter.setPen(QColor("#ffffff") if cabecalho else QColor("#243447"))
            tamanho = 9 if cabecalho else 8
            painter.setFont(QFont("Arial", tamanho, QFont.Bold if cabecalho else QFont.Normal))
            # Impede que textos longos invadam a célula vizinha.
            texto = painter.fontMetrics().elidedText(str(texto), Qt.ElideRight, largura_celula - 24)
            painter.drawText(QRect(x + 12, y, largura_celula - 24, alturas), Qt.AlignVCenter | Qt.AlignLeft, texto)

        painter.setPen(QColor("#173b67"))
        painter.setFont(QFont("Arial", 18, QFont.Bold))
        painter.drawText(QRect(margem, 55, tabela_largura, 55), Qt.AlignLeft | Qt.AlignVCenter, "Relatório de Cadastros")
        painter.setPen(QColor("#718096"))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(QRect(margem, 110, tabela_largura, 35), Qt.AlignLeft | Qt.AlignVCenter, "Registros exibidos no sistema")

        y = 175
        x = margem
        for titulo, largura_coluna in zip(colunas, larguras):
            desenhar_celula(x, y, largura_coluna, titulo, True)
            x += largura_coluna
        y += alturas

        for linha in range(self.tabela.rowCount()):
            valores = [self.tabela.item(linha, coluna).text() for coluna in range(6)]
            if y + alturas > pdf.height() - 80:
                pdf.newPage()
                y = 80
                x = margem
                for titulo, largura_coluna in zip(colunas, larguras):
                    desenhar_celula(x, y, largura_coluna, titulo, True)
                    x += largura_coluna
                y += alturas
            x = margem
            for valor, largura_coluna in zip(valores, larguras):
                desenhar_celula(x, y, largura_coluna, valor, False)
                x += largura_coluna
            y += alturas
        painter.end()
        QMessageBox.information(self, "PDF", "Tabela exportada com sucesso!")


if __name__ == "__main__":
    criar_banco()
    app = QApplication(sys.argv)
    janela = Janela()
    janela.show()
    sys.exit(app.exec())