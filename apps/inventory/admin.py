from django.contrib import admin
from .models import Item

@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display  = ('sku', 'name', 'category', 'total_stock')
    list_filter   = ('category',)
    search_fields = ('sku', 'name')
    ordering      = ('sku',)
    readonly_fields = ()  # adicione aqui campos apenas-leitura, se quiser

    fieldsets = (
        (None, {
            'fields': ('sku', 'name', 'category', 'total_stock')
        }),
    )