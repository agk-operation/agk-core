from django.db import models
from django.core.files.base import ContentFile
from io import BytesIO
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from apps.orders.models import Order
import os


class PaymentCondition(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Payment Condition"
        verbose_name_plural = "Payment Conditions"

    def __str__(self) -> str:
        return self.name
    

def proforma_invoice_upload_path(instance, filename):
    """
    Gera um path tipo:
      proforma_invoices/order_<order_pk>/proforma_invoice_<pi_pk>.pdf
    """
    order_pk = instance.order.pk
    pi_pk = instance.pk
    name = f'proforma_invoice_order_{order_pk}_{pi_pk}.pdf'
    return os.path.join('proforma_invoices', f'order_{order_pk}', name)

class ProformaInvoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='proforma')
    created_at = models.DateTimeField(auto_now_add=True)
    usd_rmb = models.DecimalField(max_digits=10, decimal_places=4)
    payment_terms = models.CharField(max_length=255)
    deposit_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    pdf = models.FileField(
        upload_to=proforma_invoice_upload_path,
        blank=True, null=True,
        help_text="Arquivo PDF gerado da Proforma Invoice"
    )

    def __str__(self):
        return f"PI #{self.pk} para Order #{self.order.pk}"

    def generate_pdf(self):
        # 1) Renderiza o HTML
        html = render_to_string('finance/proforma_invoice_pdf.html', {
            'pi': self,
            'items': [
                {
                    'code': it.item.s_code,
                    'name': it.item.name,
                    'sale_price': it.sale_price,
                    'quantity': it.quantity,
                    'total': it.total,
                }
                for it in self.order.order_items.select_related('item').all()
            ],
            'total_sum': sum(it.total for it in self.order.order_items.all()),
        })
        # 2) Gera PDF em memória
        result = BytesIO()
        status = pisa.CreatePDF(html, dest=result)
        if status.err:
            raise RuntimeError(f"Erro ao gerar PDF: {status.err}")

        # 3) Salva o arquivo no FileField e no banco
        filename = f'proforma_invoice_{self.order.pk}_{self.pk}.pdf'
        self.pdf.save(filename, ContentFile(result.getvalue()), save=True)

    def delete(self, *args, **kwargs):
        # apaga o arquivo físico
        if self.pdf:
            self.pdf.delete(save=False)
        # destrava order
        self.order.is_locked = False
        self.order.save()
        return super().delete(*args, **kwargs)