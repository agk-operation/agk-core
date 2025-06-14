from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce
from apps.core.models import Customer, Exporter, Company
from apps.inventory.models import Item

class Order(models.Model):
    customer  = models.ForeignKey(Customer, on_delete=models.PROTECT)
    exporter = models.ForeignKey(Exporter, on_delete=models.PROTECT)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_item_balances(self):
        """
        Retorna um queryset de OrderItem já anotado com:
         - shipped: total já embarcado (soma de BatchItem.quantity)
         - remaining: quantidade restante (order.quantity - shipped)
        """
        return (
            self.order_items
                .annotate(shipped_qty=Sum('batchitem__quantity'))
                .annotate(
                    shipped_qty=models.F('shipped_qty'),
                    remaining=models.F('quantity') - models.F('shipped_qty')
                )
        )

    def __str__(self):
        return f"Ordem #{self.pk} - {self.customer.name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    @property
    def shipped_qty(self):
        """Soma todas as quantidades já embarcadas neste OrderItem."""
        shipped = (
            self.batchitem_set
                .aggregate(total=Sum('quantity'))['total']
        )
        return shipped or 0

    @property
    def remaining_qty(self):
        """Quantidade que ainda resta embarcar."""
        return self.quantity - self.shipped_qty

    def __str__(self):
        return f"{self.item.name} ({self.quantity})"

class OrderBatch(models.Model):
    STATUS_CHOICES = [
        ('created',   'Criado'),
        ('pending',   'Pendente'),
        ('shipped',   'Enviado'),
        ('cancelled', 'Cancelado'),
    ]

    order = models.ForeignKey(Order, related_name='batches', on_delete=models.CASCADE)
    batch_code = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lote {self.batch_code} — {self.get_status_display()}"

class BatchItem(models.Model):
    batch = models.ForeignKey(OrderBatch, related_name='batch_items', on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem,  on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.order_item.item.name} ({self.quantity})"
