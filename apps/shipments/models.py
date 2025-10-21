from django.db import models
from apps.orders.models import OrderBatch
from apps.core.models import Agent, Carrier, Port, City


class Shipment(models.Model):
    # Status Choices...
    STATUS_PRELOADING = 'PRE'
    STATUS_READY = 'RDY'
    STATUS_SHIPPED = 'SHP'
    STATUS_CHOICES = [
        (STATUS_PRELOADING, 'Pre-Loading'),
        (STATUS_READY, 'Ready to Load'),
        (STATUS_SHIPPED, 'Shipped'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default=STATUS_PRELOADING)

    pol = models.ForeignKey(
        Port, 
        on_delete=models.PROTECT, 
        verbose_name="Port of Loading", 
        max_length=100, 
        blank=True,
        related_name="shipments_pol"  # ✅ unique related_name
    )
    pod = models.ForeignKey(
        Port, 
        on_delete=models.PROTECT, 
        verbose_name="Port of Destination", 
        max_length=100, 
        blank=True,
        related_name="shipments_pod"  # ✅ unique related_name
    )
    signer = models.CharField("Signer", max_length=100, blank=True)
    leader = models.CharField("Leader", max_length=100, blank=True)
    customer_reference = models.CharField("Customer Ref.", max_length=100, blank=True)

    loading_date = models.DateTimeField(null=True)
    shipping_date = models.DateField(null=True, blank=True)

    cons_point = models.ForeignKey(
        City, 
        on_delete=models.PROTECT, 
        verbose_name="Consolidation Point", 
        max_length=100, 
        blank=True,
        related_name="shipments_cons_point"  # ✅ unique related_name
    )
    city = models.ForeignKey(
        City, 
        on_delete=models.PROTECT, 
        verbose_name="City", 
        max_length=100, 
        blank=True,
        related_name="shipments_city"  # ✅ unique related_name
    )

    shp_doc = models.FileField(
        "Shipping Document", 
        upload_to='shipment_document/%Y/%m/%d/', 
        blank=True, 
        null=True
    )
    carrier = models.ForeignKey(
        Carrier, 
        on_delete=models.PROTECT, 
        verbose_name="Carrier", 
        max_length=200, 
        blank=True,
        related_name="shipments"  # Optional: add related_name here too
    )
    origin_agent = models.ForeignKey(
        Agent, 
        on_delete=models.PROTECT, 
        verbose_name="Origin Agent",
        related_name="shipments_origin"  # ✅ unique related_name
    )
    destination_agent = models.ForeignKey(
        Agent, 
        on_delete=models.PROTECT, 
        verbose_name="Destination Agent",
        related_name="shipments_destination"  # ✅ unique related_name
    )

    agents_note = models.TextField(blank=True)
    tracking_number = models.CharField("Tracking Number", max_length=200, blank=True)

    booking = models.FileField(
        "Booking Document", 
        upload_to='booking_document/%Y/%m/%d/', 
        blank=True, 
        null=True
    )

    notes = models.TextField(blank=True)
    bl_number = models.CharField("B.L Number", max_length=200, blank=True)
    bl_date = models.DateTimeField("B.L Date", null=True)
    inspection_no = models.CharField("Inspection Number", max_length=200, blank=True)
    eta_destination = models.DateField("E.T.A", null=True, blank=True)
    ata_destination = models.DateField("A.T.A", null=True, blank=True)

    batches = models.ManyToManyField(
        OrderBatch,
        through='ShipmentBatch',
        related_name='shipments'
    )

    @property
    def is_preloading(self): 
        return self.status == self.STATUS_PRELOADING

    @property
    def is_ready(self):
        return self.status == self.STATUS_READY

    @property
    def is_shipped(self): 
        return self.status == self.STATUS_SHIPPED

    def is_pre_phase_completed(self):
        required_fields = [
            self.cons_point,
            self.city,
            self.pol,
            self.shp_doc,
            self.origin_agent,
            self.destination_agent,
            self.booking,
        ]
        return all(required_fields)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Shipment #{self.pk} ({self.get_status_display()})"



class ShipmentBatch(models.Model):
    shipment = models.ForeignKey(
        Shipment, 
        on_delete=models.CASCADE, 
        related_name='shipment_batches'
    )
    order_batch = models.ForeignKey(OrderBatch, on_delete=models.PROTECT, related_name='in_shipments')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('shipment','order_batch')

    def __str__(self):
        return f"{self.order_batch} em Shipment#{self.shipment.pk}"


class Stage(models.Model):
    # define qual workflow cada etapa pertence
    WORKFLOW_PRELOADING = 'PRE'
    WORKFLOW_SHIPMENT   = 'SHP'
    WORKFLOW_CHOICES = [
        (WORKFLOW_PRELOADING, 'Pre-Loading'),
        (WORKFLOW_SHIPMENT,   'Shipment'),
    ]

    name = models.CharField("Etapa", max_length=100)
    description = models.TextField(blank=True, null=True)
    workflow = models.CharField(max_length=3, choices=WORKFLOW_CHOICES)
    sort_order  = models.PositiveIntegerField(default=0)
    allows_attachment  = models.BooleanField(
        default=True,
        help_text="If not checked, do not show the attachment field"
    )
    requires_attachment = models.BooleanField(
        default=False,
        help_text="If checked, turns attachment field requireds when actual_completion=True"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['workflow','sort_order','name']

    def __str__(self):
        return f"[{self.get_workflow_display()}] {self.name}"


class ShipmentStage(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='stages')
    stage = models.ForeignKey(Stage, on_delete=models.PROTECT, related_name='+')
    # datas previstas e reais
    estimated_completion = models.DateField("Estimated", null=True, blank=True)
    actual_completion = models.DateField("Actual", null=True, blank=True)
    # comentários e documento
    notes = models.TextField("Observations", blank=True)
    attachment = models.FileField(
        "Attachment", 
        upload_to='shipment_stages/%Y/%m/%d/', 
        blank=True, 
        null=True
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('shipment','stage')
        ordering = ['stage__sort_order']

    def __str__(self):
        return f"{self.shipment} → {self.stage.name}"


class StageShipmentField(models.Model):
    stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        related_name='field_configs'
    )
    field_name = models.CharField(
        "Nome do campo em Shipment",
        max_length=100,
        help_text="Ex: loading_date, bl_number, origin_agent…"
    )

    class Meta:
        unique_together = ('stage','field_name')
        verbose_name = "Campo de Shipment por Etapa"
        verbose_name_plural = "Campos de Shipment por Etapa"

    def __str__(self):
        return f"{self.stage.name} → {self.field_name}"