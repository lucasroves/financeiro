# core/management/commands/popular_dados.py

import os
import csv
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# Importe todos os seus modelos do app
from core.models import (
    TaxaCartao, OperacaoCartao, FechamentoDiario, Cliente, Duplicata,
    Retirada, Despesa, Fornecedor, BoletoCompra, CompraFornecedor, ResumoMensal
)

# Mapeamento para o campo 'tipo_dia' do modelo FechamentoDiario
TIPO_DIA_MAP = {
    'FERIADO': 'FERIADO',
    'SABADO': 'SABADO',
    'DOMINGO': 'DOMINGO'
}

class Command(BaseCommand):
    help = 'Popula o banco de dados com os dados dos arquivos CSV de Janeiro.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='O caminho para a pasta que contém os arquivos CSV.')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        
        # Lista de arquivos CSV a serem processados
        files = {
            'cadastro_cartoes': '01.JANEIRO.xlsx - CADASTRO DE CARTÕES.csv',
            'fechamento': '01.JANEIRO.xlsx - FECHAMENTO.csv',
            'cartoes': '01.JANEIRO.xlsx - CARTÕES.csv',
            'duplicatas': '01.JANEIRO.xlsx - DUPLICATAS.csv',
            'boletos_compras': '01.JANEIRO.xlsx - BOLETOSCOMPRAS.csv',
            # Adicione outros arquivos se necessário (mesmo que vazios)
            'retiradas': '01.JANEIRO.xlsx - RETIRADA.csv',
            'despesas': '01.JANEIRO.xlsx - DESPESAS.csv',
            'resumo': '01.JANEIRO.xlsx - RECEITAS E DESPESAS.csv',
        }

        # Verificação da existência dos arquivos
        for key, filename in files.items():
            path = os.path.join(csv_path, filename)
            if not os.path.exists(path):
                raise CommandError(f'Arquivo não encontrado: "{path}"')

        try:
            with transaction.atomic():
                self.stdout.write(self.style.SUCCESS('Iniciando a importação em uma transação atômica...'))
                
                # Limpando dados antigos para evitar inconsistências
                self.stdout.write('Limpando dados antigos...')
                TaxaCartao.objects.all().delete()
                OperacaoCartao.objects.all().delete()
                FechamentoDiario.objects.all().delete()
                Duplicata.objects.all().delete()
                Cliente.objects.all().delete()
                BoletoCompra.objects.all().delete()
                CompraFornecedor.objects.all().delete()
                Fornecedor.objects.all().delete()
                ResumoMensal.objects.all().delete()
                Retirada.objects.all().delete()
                Despesa.objects.all().delete()

                # Importação na ordem correta
                self._importar_taxas_cartao(os.path.join(csv_path, files['cadastro_cartoes']))
                self._importar_fechamento_diario(os.path.join(csv_path, files['fechamento']))
                self._importar_operacoes_cartao(os.path.join(csv_path, files['cartoes']))
                self._importar_clientes_e_duplicatas(os.path.join(csv_path, files['duplicatas']))
                self._importar_fornecedores_boletos_compras(os.path.join(csv_path, files['boletos_compras']))
                self._importar_resumo_mensal(os.path.join(csv_path, files['resumo']))

                # Os arquivos abaixo estão vazios nos dados de exemplo, mas a lógica está aqui
                self._importar_retiradas(os.path.join(csv_path, files['retiradas']))
                self._importar_despesas(os.path.join(csv_path, files['despesas']))

        except Exception as e:
            raise CommandError(f'Ocorreu um erro durante a importação. A transação foi revertida. Erro: {e}')

        self.stdout.write(self.style.SUCCESS('Todos os dados foram importados com sucesso!'))

    def _parse_decimal(self, value_str):
        if not value_str or value_str.strip() == '#N/A':
            return None
        try:
            # Substitui vírgula por ponto, se houver, e remove espaços
            return Decimal(value_str.replace(',', '.').strip())
        except (InvalidOperation, ValueError):
            return None

    def _parse_date(self, date_str, fmt='%Y-%m-%d'):
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except (ValueError, TypeError):
            return None
            
    def _importar_taxas_cartao(self, filepath):
        self.stdout.write(f'Importando Taxas de Cartão de {filepath}...')
        with open(filepath, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                TaxaCartao.objects.update_or_create(
                    codigo_op=row['Nº \n DA OP'],
                    defaults={
                        'bandeiras': row['BANDEIRAS'],
                        'tipo_bandeira': row['BANDEIRA'],
                        'taxa_percentual': self._parse_decimal(row['TAXA (%)']),
                        'dias_compensacao': int(row['QUANTIDADES DE DIAS A COMPENSAR'])
                    }
                )
        self.stdout.write(self.style.SUCCESS(f'{TaxaCartao.objects.count()} taxas importadas.'))

    def _importar_fechamento_diario(self, filepath):
        self.stdout.write(f'Importando Fechamento Diário de {filepath}...')
        with open(filepath, mode='r', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            next(reader) # Pular cabeçalho
            next(reader) # Pular segunda linha de cabeçalho
            for row in reader:
                if not row or not row[0]: continue # Ignorar linhas vazias
                
                data = self._parse_date(row[0])
                if not data: continue

                fundo_caixa_str = row[1].upper()
                tipo_dia_val = TIPO_DIA_MAP.get(fundo_caixa_str, 'NORMAL')

                if tipo_dia_val != 'NORMAL':
                    dinheiro, credito, debito, duplicatas, cheque, total_venda = [None] * 6
                else:
                    dinheiro = self._parse_decimal(row[2])
                    credito = self._parse_decimal(row[3])
                    debito = self._parse_decimal(row[4])
                    duplicatas = self._parse_decimal(row[5])
                    cheque = self._parse_decimal(row[6])
                    total_venda = self._parse_decimal(row[7])

                FechamentoDiario.objects.update_or_create(
                    data=data,
                    defaults={
                        'fundo_caixa': self._parse_decimal(row[1]) if tipo_dia_val == 'NORMAL' else None,
                        'dinheiro': dinheiro,
                        'credito': credito,
                        'debito': debito,
                        'duplicatas': duplicatas,
                        'cheque': cheque,
                        'total_venda': total_venda or Decimal('0.00'),
                        'tipo_dia': tipo_dia_val
                    }
                )
        self.stdout.write(self.style.SUCCESS(f'{FechamentoDiario.objects.count()} registros de fechamento importados.'))

    def _importar_operacoes_cartao(self, filepath):
        self.stdout.write(f'Importando Operações de Cartão de {filepath}...')
        with open(filepath, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                data = self._parse_date(row.get('data'))
                if not data or row.get('Nº DA OP') == '#N/A': continue
                
                OperacaoCartao.objects.create(
                    data=data,
                    numero_op=row['Nº DA OP'].upper(),
                    valor_bruto=self._parse_decimal(row['VALOR BRUTO']),
                    taxa=self._parse_decimal(row['TAXA (%)']),
                    valor_liquido=self._parse_decimal(row['VALOR LIQUIDO']),
                    desconto=self._parse_decimal(row['DESCONTO']),
                )
        self.stdout.write(self.style.SUCCESS(f'{OperacaoCartao.objects.count()} operações de cartão importadas.'))

    def _importar_clientes_e_duplicatas(self, filepath):
        self.stdout.write(f'Importando Clientes e Duplicatas de {filepath}...')
        with open(filepath, mode='r', encoding='utf-8') as csv_file:
            # Pula as duas primeiras linhas de cabeçalho
            next(csv_file, None)
            next(csv_file, None)
            reader = csv.DictReader(csv_file, fieldnames=['data_emissao', 'codigo', 'cliente', 'bruto', 'col5', 'col6', 'col7', 'col8'])
            for row in reader:
                cliente_nome = row['cliente'].strip()
                if not cliente_nome or 'total' in cliente_nome.lower(): continue

                # Cria o cliente se não existir
                cliente_obj, created = Cliente.objects.get_or_create(
                    nome=cliente_nome
                )
                if created:
                    self.stdout.write(f'Cliente criado: {cliente_nome}')

                data_emissao = self._parse_date(row['data_emissao'])
                if not data_emissao: continue

                Duplicata.objects.create(
                    data_emissao=data_emissao,
                    cliente=cliente_obj,
                    valor_bruto=self._parse_decimal(row['bruto']),
                    pago=False, # Default, pois não há essa info no CSV
                )
        self.stdout.write(self.style.SUCCESS(f'{Cliente.objects.count()} clientes e {Duplicata.objects.count()} duplicatas importados.'))

    def _importar_fornecedores_boletos_compras(self, filepath):
        self.stdout.write(f'Importando Fornecedores, Boletos e Compras de {filepath}...')
        with open(filepath, mode='r', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            # Pula cabeçalho
            next(reader, None)

            for row in reader:
                if not any(row): continue # Ignora linhas vazias
                
                # Parte 1: Boletos de Compra (colunas da esquerda)
                fornecedor_nome = row[1].strip()
                if fornecedor_nome:
                    fornecedor_obj, created = Fornecedor.objects.get_or_create(nome=fornecedor_nome)
                    if created: self.stdout.write(f'Fornecedor criado: {fornecedor_nome}')

                    BoletoCompra.objects.create(
                        data_vencimento=self._parse_date(row[0]),
                        fornecedor=fornecedor_obj,
                        numero_documento=row[2],
                        valor=self._parse_decimal(row[3]),
                        data_pagamento=self._parse_date(row[4]),
                        pago=bool(row[4].strip())
                    )

                # Parte 2: Compras de Fornecedor (colunas da direita)
                compra_fornecedor_nome = row[6].strip()
                if compra_fornecedor_nome:
                    compra_fornecedor_obj, created = Fornecedor.objects.get_or_create(nome=compra_fornecedor_nome)
                    if created: self.stdout.write(f'Fornecedor (de compra) criado: {compra_fornecedor_nome}')

                    data_compra = self._parse_date(row[7])
                    valor_compra = self._parse_decimal(row[8])

                    if data_compra and valor_compra:
                        CompraFornecedor.objects.create(
                            descricao=f"Compra de {compra_fornecedor_nome}",
                            data=data_compra,
                            valor=valor_compra,
                            fornecedor=compra_fornecedor_obj
                        )

        self.stdout.write(self.style.SUCCESS(f'{Fornecedor.objects.count()} fornecedores, {BoletoCompra.objects.count()} boletos e {CompraFornecedor.objects.count()} compras importados.'))

    def _importar_resumo_mensal(self, filepath):
        self.stdout.write(f'Importando Resumo Mensal de {filepath}...')
        with open(filepath, mode='r', encoding='utf-8') as csv_file:
            data = {line.split(',')[0].strip(): line.split(',')[1].strip() for line in csv_file if ',' in line}

        # Criando um único registro para Janeiro de 2025
        ResumoMensal.objects.create(
            mes='2025-01-01',
            receita_vendas=self._parse_decimal(data.get('RECEITA DE VENDAS', '0')),
            despesas_fornecedor=self._parse_decimal(data.get('COMPRAS FORNECEDOR', '0')), # Assumindo que este campo corresponde
            despesas_variaveis=self._parse_decimal(data.get('DESPESAS VARIÁVEIS', '0')),
            despesas_casa=self._parse_decimal(data.get('DESPESAS CASA', '0')),
            despesas_pessoais=self._parse_decimal(data.get('GILCEU', '0')), # Mapeando 'GILCEU' para despesas pessoais
            
            # Detalhes de despesas
            aluguel_empresa=self._parse_decimal(data.get('ALUGUEL', '1600')),
            honorarios_contador=self._parse_decimal(data.get('HONORÁRIOS CONTADOR', '706')),
            sistema_alterdata=self._parse_decimal(data.get('SISTEMA ALTERDATA', '352.73')),
            telefonia_internet=self._parse_decimal(data.get('TELEFONIA/INTERNET', '240')),
            salario_funcionarios=self._parse_decimal(data.get('SALÁRIO DE FUNCIONARIOS', '4000')),
            boletos_duplicatas=self._parse_decimal(data.get('BOLETOS E DUPLICATAS', '0')),
        )
        self.stdout.write(self.style.SUCCESS(f'{ResumoMensal.objects.count()} resumo mensal importado.'))

    def _importar_retiradas(self, filepath):
        # O arquivo de exemplo está vazio, mas a lógica de importação estaria aqui.
        self.stdout.write(f'Arquivo de Retiradas ({filepath}) está vazio ou não contém dados. Pulando.')

    def _importar_despesas(self, filepath):
        # O arquivo de exemplo está vazio, mas a lógica de importação estaria aqui.
        self.stdout.write(f'Arquivo de Despesas ({filepath}) está vazio ou não contém dados. Pulando.')