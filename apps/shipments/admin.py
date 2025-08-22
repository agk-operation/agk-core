# apps/shipments/admin.py

from django.contrib import admin
from .models import (
    Shipment,
    ShipmentBatch,
    Stage,
    ShipmentStage,
    StageShipmentField,
)


class ShipmentBatchInline(admin.TabularInline):
    model = ShipmentBatch
    extra = 1
    autocomplete_fields = ('order_batch',)
    fields = ('order_batch', 'created_at')
    readonly_fields = ('created_at',)


class ShipmentStageInline(admin.StackedInline):
    model = ShipmentStage
    extra = 0
    fields = (
        'stage',
        'estimated_completion',
        'actual_completion',
        'notes',
        'attachment',
        'created_at',
    )
    readonly_fields = ('created_at',)
    ordering = ('stage__sort_order',)


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'pk',
        'get_status_display',
        'created_at',
        'pol',
        'pod',
        'signer',
        'leader',
        'customer_reference',
        'shipping_date',
        'carrier',
    )
    list_filter = ('status', 'created_at')
    date_hierarchy = 'created_at'
    search_fields = (
        'pol', 'signer', 'leader', 'customer_reference',
        'carrier', 'tracking_number',
    )
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ShipmentBatchInline, ShipmentStageInline]


class StageShipmentFieldInline(admin.TabularInline):
    model = StageShipmentField
    extra = 1


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display    = ('name','workflow','sort_order')
    inlines         = [StageShipmentFieldInline]
    ordering        = ('workflow','sort_order')
    search_fields = ('name',)