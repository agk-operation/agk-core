from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from apps.inventory.models import Item
from apps.core.models import Customer


class CustomerItemMargin(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    item  = models.ForeignKey(Item, on_delete=models.CASCADE)
    margin = models.DecimalField(
        "Margem padrão (%)",
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Ex.: 20 = 20%"
    )

    class Meta:
        unique_together = ('customer', 'item')
        verbose_name = "Margem por Cliente/Item"
        verbose_name_plural = "Margens por Cliente/Item"

    def __str__(self):
        return f"{self.customer} – {self.item}: {self.margin}%"
