from django.contrib import admin
from . import models


class ExporterInline(admin.TabularInline):
    model = models.Exporter
    extra = 1


@admin.register(models.Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'country')
    search_fields = ('name',)
    inlines = [ExporterInline]


@admin.register(models.Exporter)
class ExporterAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')
    list_filter = ('company',)
    search_fields = ('name',)


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'address')
    search_fields = ('name', 'email')
    list_filter = ()


@admin.register(models.Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'address')
    search_fields = ('name', 'email')
    list_filter = ()


@admin.register(models.City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ()


@admin.register(models.Province)
class ProvinceAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ()


@admin.register(models.Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ()


@admin.register(models.BusinessUnit)
class BusinessUnitAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ()


@admin.register(models.Port)
class PortAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ()


@admin.register(models.Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ()


@admin.register(models.OrderType)
class OrderTypeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ()


@admin.register(models.SalesRepresentative)
class SalesRepresentativeAdmin(admin.ModelAdmin):
    list_display = [f.name for f in models.SalesRepresentative._meta.fields] + ['get_customers']
    search_fields = ('name', 'email', 'phone')
    ordering      = ('name',)
    filter_vertical = ()
    fieldsets = (
        (None, {
            'fields': ('name', 'email', 'phone')
        }),
    )
    def get_customers(self, obj):
        return ", ".join(c.name for c in obj.customers.all())
    get_customers.short_description = 'Customers'

class SalesRepresentativeCustomerInline(admin.TabularInline):
    model = models.SalesRepresentativeCustomer
    fk_name = 'representative'
    extra   = 1
    autocomplete_fields = ('customer',)

SalesRepresentativeAdmin.inlines = [SalesRepresentativeCustomerInline]
