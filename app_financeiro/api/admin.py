from django.contrib import admin
from .models import *

@admin.register(TaxaCartao)
class TaxaCartaoAdmin(admin.ModelAdmin):
    list_display = ['codigo_op', 'tipo_bandeira', 'taxa_percentual', 'dias_compensacao']
    list_filter = ['tipo_bandeira']

@admin.register(OperacaoCartao)
class OperacaoCartaoAdmin(admin.ModelAdmin):
    list_display = ['data', 'numero_op', 'valor_bruto', 'valor_liquido', 'desconto']
    list_filter = ['data', 'numero_op']
    date_hierarchy = 'data'

@admin.register(FechamentoDiario)
class FechamentoDiarioAdmin(admin.ModelAdmin):
    list_display = ['data', 'total_venda', 'dinheiro', 'credito', 'debito', 'duplicatas']
    list_filter = ['tipo_dia', 'data']
    date_hierarchy = 'data'

# Registrar todos os models no admin
admin.site.register(Cliente)
admin.site.register(Duplicata)
admin.site.register(Retirada)
admin.site.register(Despesa)
admin.site.register(Fornecedor)
admin.site.register(BoletoCompra)
admin.site.register(CompraFornecedor)
admin.site.register(ResumoMensal)
admin.site.register(VendaDiaria)
admin.site.register(DespesaFixa)
