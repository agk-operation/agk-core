from django.db import models
from apps.core.models import Category


class Item(models.Model):
    sku         = models.CharField(max_length=50, unique=True)
    name        = models.CharField(max_length=200)
    category    = models.ForeignKey(Category, on_delete=models.PROTECT)
    total_stock = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name
