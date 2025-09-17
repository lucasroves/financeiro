from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Base(models.Model):
    criacao = models.DateTimeField(auto_now_add=True)
    atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class TaxaCartao(models.Model):
    codigo_op = models.CharField("Código OP", max_length=10, unique=True)
    bandeiras = models.TextField("Bandeiras")
    tipo_bandeira = models.CharField("Tipo Bandeira", max_length=50)
    taxa_percentual = models.DecimalField("Taxa (%)", max_digits=5, decimal_places=4)
    dias_compensacao = models.IntegerField("Dias para Compensar")

    class Meta:
        verbose_name = "Taxa de Cartão"
        verbose_name_plural = "Taxas de Cartão"

    def __str__(self):
        return f"{self.codigo_op} - {self.tipo_bandeira} ({self.taxa_percentual}%)"

class OperacaoCartao(Base):
    TIPO_OPERACAO = [
        ('D1', 'Débito'),
        ('C0', 'Crédito'),
        ('C1', 'Crédito à Vista'),
        ('C2', 'Crédito 2x'),
        ('C3', 'Crédito 3x'),
        ('C4', 'Crédito 4x'),
        ('C5', 'Crédito 5x'),
        ('CP1', 'Crédito à Vista (Bandeiras Especiais)'),
        ('CP2', 'Crédito Parcelado (Bandeiras Especiais)'),
    ]
    
    data = models.DateField("Data")
    numero_op = models.CharField("Nº OP", max_length=10, choices=TIPO_OPERACAO)
    valor_bruto = models.DecimalField("Valor Bruto", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    taxa = models.DecimalField("Taxa (%)", max_digits=5, decimal_places=4)
    valor_liquido = models.DecimalField("Valor Líquido", max_digits=10, decimal_places=2)
    desconto = models.DecimalField("Desconto", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Operação de Cartão"
        verbose_name_plural = "Operações de Cartão"
        ordering = ['-data', 'numero_op']

    def save(self, *args, **kwargs):
        # Calcula automaticamente os valores se não forem fornecidos
        if not self.valor_liquido:
            self.valor_liquido = self.valor_bruto - (self.valor_bruto * self.taxa)
        if not self.desconto:
            self.desconto = self.valor_bruto - self.valor_liquido
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.data} - {self.get_numero_op_display()} - R$ {self.valor_bruto}"

class FechamentoDiario(Base):
    data = models.DateField("Data", unique=True)
    fundo_caixa = models.DecimalField("Fundo de Caixa", max_digits=10, decimal_places=2, null=True, blank=True)
    dinheiro = models.DecimalField("Dinheiro", max_digits=10, decimal_places=2, null=True, blank=True)
    credito = models.DecimalField("Crédito", max_digits=10, decimal_places=2, null=True, blank=True)
    debito = models.DecimalField("Débito", max_digits=10, decimal_places=2, null=True, blank=True)
    duplicatas = models.DecimalField("Duplicatas", max_digits=10, decimal_places=2, null=True, blank=True)
    cheque = models.DecimalField("Cheque", max_digits=10, decimal_places=2, null=True, blank=True)
    total_venda = models.DecimalField("Total de Venda", max_digits=10, decimal_places=2)

    TIPO_DIA = [
        ('NORMAL', 'Dia Normal'),
        ('FERIADO', 'Feriado'),
        ('SABADO', 'Sábado'),
        ('DOMINGO', 'Domingo'),
    ]
    tipo_dia = models.CharField("Tipo do Dia", max_length=10, choices=TIPO_DIA, default='NORMAL')

    class Meta:
        verbose_name = "Fechamento Diário"
        verbose_name_plural = "Fechamentos Diários"
        ordering = ['-data']

    def __str__(self):
        return f"Fechamento {self.data} - R$ {self.total_venda}"

class Cliente(Base):
    nome = models.CharField("Nome", max_length=255)
    codigo = models.CharField("Código", max_length=20, null=True, blank=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Duplicata(Base):
    data_emissao = models.DateField("Data de Emissão")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='duplicatas')
    valor_bruto = models.DecimalField("Valor Bruto", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    pago = models.BooleanField("Pago", default=False)
    data_pagamento = models.DateField("Data de Pagamento", null=True, blank=True)

    class Meta:
        verbose_name = "Duplicata"
        verbose_name_plural = "Duplicatas"
        ordering = ['-data_emissao']

    def __str__(self):
        return f"Duplicata {self.id} - {self.cliente} - R$ {self.valor_bruto}"

class Retirada(Base):
    TIPO_CATEGORIA = [
        ('CASA', 'Despesas da Casa'),
        ('EMPRESA', 'Despesas da Empresa'),
        ('PESSOAL', 'Despesas Pessoais'),
    ]
    
    descricao = models.CharField("Descrição", max_length=255)
    data = models.DateField("Data")
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    categoria = models.CharField("Categoria", max_length=20, choices=TIPO_CATEGORIA)
    subcategoria = models.CharField("Subcategoria", max_length=100, null=True, blank=True)

    class Meta:
        verbose_name = "Retirada"
        verbose_name_plural = "Retiradas"
        ordering = ['-data']

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor}"

class Despesa(Base):
    descricao = models.CharField("Descrição", max_length=255)
    data = models.DateField("Data")
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    categoria = models.CharField("Categoria", max_length=100)
    combustivel_moto = models.BooleanField("Combustível Moto", default=False)

    class Meta:
        verbose_name = "Despesa"
        verbose_name_plural = "Despesas"
        ordering = ['-data']

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor}"

class Fornecedor(Base):
    nome = models.CharField("Nome", max_length=255)
    cnpj = models.CharField("CNPJ", max_length=20, null=True, blank=True)
    telefone = models.CharField("Telefone", max_length=20, null=True, blank=True)
    email = models.EmailField("Email", null=True, blank=True)
    
    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"
        ordering = ['nome']

    def __str__(self):
        return self.nome

class BoletoCompra(Base):
    data_vencimento = models.DateField("Data de Vencimento")
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, related_name='boletos')
    numero_documento = models.CharField("Número do Documento", max_length=100, null=True, blank=True)
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    data_pagamento = models.DateField("Data de Pagamento", null=True, blank=True)
    pago = models.BooleanField("Pago", default=False)

    class Meta:
        verbose_name = "Boleto de Compra"
        verbose_name_plural = "Boletos de Compra"
        ordering = ['-data_vencimento']

    def __str__(self):
        return f"Boleto {self.numero_documento} - {self.fornecedor} - R$ {self.valor}"

class CompraFornecedor(Base):
    descricao = models.CharField("Descrição", max_length=255)
    data = models.DateField("Data")
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, related_name='compras')

    class Meta:
        verbose_name = "Compra de Fornecedor"
        verbose_name_plural = "Compras de Fornecedores"
        ordering = ['-data']

    def __str__(self):
        return f"{self.descricao} - {self.fornecedor} - R$ {self.valor}"

class ResumoMensal(Base):


    mes = models.DateField("Mês")
    receita_vendas = models.DecimalField("Receita de Vendas", max_digits=15, decimal_places=2)
    despesas_fornecedor = models.DecimalField("Despesas com Fornecedor", max_digits=15, decimal_places=2)
    despesas_variaveis = models.DecimalField("Despesas Variáveis", max_digits=15, decimal_places=2)
    despesas_casa = models.DecimalField("Despesas da Casa", max_digits=15, decimal_places=2)
    despesas_pessoais = models.DecimalField("Despesas Pessoais", max_digits=15, decimal_places=2)
    total_liquido = models.DecimalField("Total Líquido", max_digits=15, decimal_places=2)

    # Despesas Fixas da Empresa
    aluguel_empresa = models.DecimalField("Aluguel Empresa", max_digits=10, decimal_places=2, default=1600.00)
    honorarios_contador = models.DecimalField("Honorários Contador", max_digits=10, decimal_places=2, default=706.00)
    sistema_alterdata = models.DecimalField("Sistema Alterdata", max_digits=10, decimal_places=2, default=352.73)
    telefonia_internet = models.DecimalField("Telefonia/Internet", max_digits=10, decimal_places=2, default=240.00)

    # Despesas Variáveis da Empresa
    compras_locais = models.DecimalField("Compras Lojas Locais", max_digits=10, decimal_places=2, default=0)
    salario_funcionarios = models.DecimalField("Salário Funcionários", max_digits=10, decimal_places=2, default=4000.00)
    desconto_cartao = models.DecimalField("Desconto Cartão", max_digits=10, decimal_places=2, default=0)
    boletos_duplicatas = models.DecimalField("Boletos e Duplicatas", max_digits=10, decimal_places=2, default=0)
    multas_encargos = models.DecimalField("Multas e Encargos", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Resumo Mensal"
        verbose_name_plural = "Resumos Mensais"
        unique_together = ['mes']
        ordering = ['-mes']

    def save(self, *args, **kwargs):
        # Calcula automaticamente o total líquido
        despesas_fixas = self.aluguel_empresa + self.honorarios_contador + self.sistema_alterdata + self.telefonia_internet
        despesas_variaveis = self.compras_locais + self.salario_funcionarios + self.desconto_cartao + self.boletos_duplicatas + self.multas_encargos
        
        self.total_liquido = self.receita_vendas - despesas_fixas - despesas_variaveis - self.despesas_casa - self.despesas_pessoais
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Resumo {self.mes.strftime('%B/%Y')} - R$ {self.total_liquido}"
    
class VendaDiaria(Base):
    fechamento = models.ForeignKey(FechamentoDiario, on_delete=models.CASCADE, related_name='vendas')
    tipo_venda = models.CharField("Tipo de Venda", max_length=20, choices=[
        ('DINHEIRO', 'Dinheiro'),
        ('CREDITO', 'Crédito'),
        ('DEBITO', 'Débito'),
        ('DUPLICATA', 'Duplicata'),
        ('CHEQUE', 'Cheque'),
    ])
    valor = models.DecimalField("Valor", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Venda Diária"
        verbose_name_plural = "Vendas Diárias"

class DespesaFixa(Base):
    descricao = models.CharField("Descrição", max_length=255)
    valor_mensal = models.DecimalField("Valor Mensal", max_digits=10, decimal_places=2)
    ativa = models.BooleanField("Ativa", default=True)

    class Meta:
        verbose_name = "Despesa Fixa"
        verbose_name_plural = "Despesas Fixas"

    def __str__(self):
        return f"{self.descricao} - R$ {self.valor_mensal}/mês"