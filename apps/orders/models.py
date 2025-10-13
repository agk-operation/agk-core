from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db.models import Sum
from apps.core.models import Customer, Exporter, Company, Port, SalesRepresentative, BusinessUnit, Project, OrderType
from apps.inventory.models import Item, ItemPackagingVersion


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    exporter = models.ForeignKey(Exporter, on_delete=models.PROTECT)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    validity = models.DateTimeField(null=False, blank=False)
    usd_rmb = models.DecimalField(
        max_digits=12, 
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    usd_brl = models.DecimalField(
        max_digits=12, 
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    required_schedule = models.DateTimeField(null=True, blank=True)
    asap = models.BooleanField(null=True, blank=True)
    down_payment = models.DecimalField(
        max_digits=12, 
        decimal_places=6,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Ex.: 20 = 20%",
    )
    pol = models.ForeignKey(
        Port,
        on_delete=models.PROTECT,
        related_name='orders_as_pol',
    )
    pod = models.ForeignKey(
        Port,
        on_delete=models.PROTECT,
        related_name='orders_as_pod',
    )
    sales_representative = models.ForeignKey(
        SalesRepresentative, 
        on_delete=models.PROTECT,
    )
    business_unit = models.ForeignKey(
        BusinessUnit, 
        on_delete=models.PROTECT,
    )
    project = models.ForeignKey(
        Project, 
        on_delete=models.PROTECT,
    )
    order_type = models.ForeignKey(
        OrderType, 
        on_delete=models.PROTECT,
    )
    is_locked = models.BooleanField(
        default=False, 
        help_text="No changes allowed when true"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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

    def clean(self):
        super().clean()
        if not self.asap and not self.required_schedule:
            raise ValidationError({
                'required_schedule': 'This field is required when “asap” is false.'
            })
    
    def __str__(self):
        return f"Ordem #{self.pk} - {self.customer.name}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    cost_price = models.DecimalField(
        "Cost Price",
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    cost_price_usd = models.DecimalField(
        "Dolar Cost Price",
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00')
    )
    margin = models.DecimalField(
        "Margin (%)",
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        null=True, blank=True,
        default=None,
        help_text="Ex.: 20 = 20%"
    )
    sale_price = models.DecimalField(
        "Sale Price",
        max_digits=12, 
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    packaging_version = models.ForeignKey(
        'inventory.ItemPackagingVersion',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='order_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


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

    @property
    def total(self):
        return self.sale_price * self.quantity
    
    def save(self, *args, **kwargs):
        if not self.pk and not self.packaging_version:
            self.packaging_version = self.item.current_packaging_version()
            
        if self.item.currency == 'USD':
            self.cost_price_usd = self.cost_price or Decimal('0.00')
        else:
            usd_rmb = getattr(self.order, 'usd_rmb', Decimal('0.00')) or Decimal('0.00')
            self.cost_price_usd = (self.cost_price * usd_rmb).quantize(Decimal('0.01')) or Decimal('0.00')

        margin = self.margin if self.margin is not None else Decimal("0.00")
        factor = Decimal("1.00") + (margin / Decimal("100.00"))
        self.sale_price = (self.cost_price_usd * factor).quantize(Decimal("0.01"))

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} ({self.remaining_qty})"
    
    class Meta:
        ordering = ['pk']
    

class OrderBatch(models.Model):
    STATUS_CHOICES = [
        ('negotiation', 'In Negotiation'),
        ('production', 'In Production'),
        ('pre', 'Pre Shipment'),
        ('pre', 'Pre Shipment'),
        ('transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('stb', 'Stand by'),
        ('canceled', 'Canceled'),
    ]

    order = models.ForeignKey(Order, related_name='batches', on_delete=models.CASCADE)
    batch_code = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"Lote {self.batch_code} — {self.get_status_display()}"


class BatchItem(models.Model):
    batch = models.ForeignKey(OrderBatch, related_name='batch_items', on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem,  on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order_item.item.name} ({self.quantity})"
 

class Stage(models.Model):
    name = models.CharField("Etapa", max_length=100)
    description = models.TextField(blank=True, null=True)
    sort_order  = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stage"
        verbose_name_plural = "Stages"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name}"
       

class BatchStage(models.Model):
    batch = models.ForeignKey(
        OrderBatch,
        on_delete=models.CASCADE,
        related_name='stages'
    )
    stage = models.ForeignKey(
        Stage, 
        on_delete=models.CASCADE,
        related_name='batch_stage',
    )
    estimated_completion = models.DateField(
        "Estimed Date",
        null=True,
        blank=True,
    )
    actual_completion = models.DateField(
        "Actual Date",
        null=True,
        blank=True
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name = "Batch Stage"
        verbose_name_plural = "Batch Stages"
        ordering = ['stage__sort_order']

    def __str__(self):
        return f"{self.stage.name} — {self.estimated_completion or 'No Date Yet'}"

