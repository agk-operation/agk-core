from django.contrib import admin
from .models import Order, OrderItem, OrderBatch, BatchItem, BatchStage, Stage


# —— Inline para OrderItem dentro de Order ——
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ()  # customize se quiser


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('id', 'customer', 'exporter', 'company', 'created_at')
    list_filter   = ('customer', 'exporter', 'company')
    search_fields = ('customer__name', 'exporter__name')
    inlines       = [OrderItemInline]


# —— Inline para BatchItem dentro de OrderBatch, com dados do OrderItem ——
class BatchItemInline(admin.TabularInline):
    model = BatchItem
    extra = 1
    fields = ('item_name', 'packaging_version', 'quantity', 'margin')
    readonly_fields = ('item_name', 'packaging_version', 'margin')

    def item_name(self, obj):
        return obj.order_item.item.name if obj.order_item else None

    def packaging_version(self, obj):
        return obj.order_item.packaging_version if obj.order_item else None

    def margin(self, obj):
        return obj.order_item.margin if obj.order_item else None

    item_name.short_description = "Item"
    packaging_version.short_description = "Packaging Version"
    margin.short_description = "Margin (%)"


# —— Inline para BatchStage dentro de OrderBatch ——
class BatchStageInline(admin.TabularInline):
    model = BatchStage
    extra = 1
    fields = ('stage', 'estimated_completion', 'actual_completion', 'active')

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and getattr(obj.order, 'is_locked', False):
            ro.append('stage')
        return ro


@admin.register(OrderBatch)
class OrderBatchAdmin(admin.ModelAdmin):
    list_display  = ('batch_code', 'order', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('batch_code',)
    inlines       = [BatchItemInline, BatchStageInline]


# —— Caso queira ver/editar BatchItem isoladamente ——
@admin.register(BatchItem)
class BatchItemAdmin(admin.ModelAdmin):
    list_display  = ('batch', 'order_item', 'quantity')
    list_filter   = ('batch__status',)
    search_fields = ('order_item__item__name',)


@admin.register(BatchStage)
class BatchStageAdmin(admin.ModelAdmin):
    list_display  = ('batch', 'estimated_completion', 'actual_completion')
    list_filter   = ('batch__status',)
    search_fields = ('batch__batch_code',)  # Corrigido typo: 'bacth' -> 'batch'


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name',)
    list_filter   = ('name',)
    search_fields = ('name',)
