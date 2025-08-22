from django.contrib import admin
from . import models


class ItemModelApplicationInline(admin.TabularInline):
    model = models.ItemModelApplication
    extra = 1


class ItemPackagingVersionInline(admin.TabularInline):
    model = models.ItemPackagingVersion
    extra = 0
    fields = (
        'valid_from','valid_to',
        'net_weight','package_gross_weight',
        'packing_lengh','packing_width','packing_height',
        'individual_packing_size','individual_packing_type',
    )


@admin.register(models.Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = [field.name for field in models.Item._meta.fields]
    list_filter   = ('category',)
    search_fields = ('p_code', 'name')
    ordering      = ('p_code',)
    readonly_fields = ()  # adicione aqui campos apenas-leitura, se quiser
    inlines = [ItemModelApplicationInline, ItemPackagingVersionInline]

    fieldsets = (
                ('Basic Data', {
                    'fields': ('name', 'category', 'subcategory', 
                               'project', 'supplier', 'supplier_chain', 'chain')
                }),
                ('Item Specifications' , {
                    'fields' : ('brand_manufacturer', 'ncm')
                }),
                ('Codes', {
                    'fields': ('p_code', 's_code')
                }),
                ('Currency Data', {
                    'fields': ('cost_price', 'selling_price', 'currency'),
                })
    )

    def get_model_applications(self, obj):
        return ", ".join(str(m) for m in obj.model_application.all())
    get_model_applications.short_description = "Model Applications"


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    list_filter = ()


@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    list_filter = ()


@admin.register(models.Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    list_filter = ()


@admin.register(models.SupplierChain)
class SupplierChainAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    list_filter = ()


@admin.register(models.Ncm)
class NcmAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    list_filter = ()


@admin.register(models.Chain)
class ChainAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    list_filter = ()


@admin.register(models.BrandManufacturer)
class BrandManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    list_filter = ()


@admin.register(models.ModelApplication)
class ModelApplicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
    list_filter = ()

    