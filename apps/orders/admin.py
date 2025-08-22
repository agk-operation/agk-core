from django.contrib import admin
from .models import Order, OrderItem, OrderBatch, BatchItem, BatchStage, Stage 

# —— Inline para OrderItem dentro de Order ——
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    readonly_fields = ()   # você pode tornar campos somente-leitura se quiser

class BatchStageInline(admin.TabularInline):
    model = BatchStage
    extra = 1
    fields = ('item', 'packaging_version', 'quantity', 'margin')

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_locked:
            ro.append('packaging_version')
        return ro


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('id', 'customer', 'exporter', 'company', 'created_at')
    list_filter   = ('customer', 'exporter', 'company')
    search_fields = ('customer__name', 'exporter__name')
    inlines       = [OrderItemInline]

# —— Inline para BatchItem dentro de OrderBatch ——
class BatchItemInline(admin.TabularInline):
    model = BatchItem
    extra = 1


@admin.register(OrderBatch)
class OrderBatchAdmin(admin.ModelAdmin):
    list_display  = ('batch_code', 'order', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('batch_code',)
    inlines       = [BatchItemInline, BatchStageInline]

# —— Caso queira ver/editar BatchItem sozinho ——
@admin.register(BatchItem)
class BatchItemAdmin(admin.ModelAdmin):
    list_display  = ('batch', 'order_item', 'quantity')
    list_filter   = ('batch__status',)
    search_fields = ('order_item__item__name',)


@admin.register(BatchStage)
class BatchStageAdmin(admin.ModelAdmin):
    list_display  = ('batch', 'estimated_completion', 'actual_completion')
    list_filter   = ('batch__status',)
    search_fields = ('bacth__batch_code',)


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display  = ('id', 'name',)
    list_filter   = ('name',)
    search_fields = ('name',)
