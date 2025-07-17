from django.contrib import admin
from django.utils.html import format_html
from .models import ProformaInvoice

@admin.register(ProformaInvoice)
class ProformaInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order', 'created_at',
        'usd_rmb', 'payment_terms', 'deposit_percentage', 'pdf_link'
    )
    list_filter = ('created_at', 'payment_terms')
    search_fields = ('order__pk', 'order__customer__name')

    readonly_fields = (
        'created_at', 'pdf', 'pdf_link'
    )
    fields = (
        'order', 'usd_rmb', 'payment_terms', 'deposit_percentage',
        'created_at', 'pdf_link', 'pdf'
    )

    def pdf_link(self, obj):
        if obj.pdf:
            return format_html('<a href="{}" target="_blank">Download PDF</a>', obj.pdf.url)
        return '-'
    pdf_link.short_description = 'Arquivo PDF'

    def get_readonly_fields(self, request, obj=None):
        ro = list(self.readonly_fields)
        # torna todos os campos não-editáveis se já existir
        if obj:
            ro += ['order', 'usd_rmb', 'payment_terms', 'deposit_percentage']
        return ro

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # garante que o PDF seja (re)gerado sempre ao salvar
        obj.generate_pdf()