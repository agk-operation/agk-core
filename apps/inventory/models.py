from django.db import models
from apps.core.models import Category, Supplier, Currency


class Project(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Subcategory(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SupplierChain(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Ncm(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Chain(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class BrandManufacturer(models.Model):
    name = models.CharField(max_length=50, unique=True)
    country = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ModelApplication(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class Item(models.Model):
    p_code = models.CharField(max_length=50, unique=True)
    s_code = models.CharField(max_length=50)

    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT)

    name = models.CharField(max_length=200)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    subcategory = models.ForeignKey(Subcategory, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    supplier_chain = models.ForeignKey(SupplierChain, on_delete=models.PROTECT)
    brand_manufacturer = models.ForeignKey(BrandManufacturer, on_delete=models.PROTECT)

    chain = models.ForeignKey(Chain, on_delete=models.PROTECT)
    ncm = models.ForeignKey(Ncm, on_delete=models.PROTECT)
    model_application = models.ManyToManyField(ModelApplication, through='ItemModelApplication')

    net_weight = models.DecimalField(max_digits=10, decimal_places=4)
    package_gross_weight = models.DecimalField(max_digits=10, decimal_places=4)
    packing_lengh = models.DecimalField(max_digits=10, decimal_places=4)
    packing_width = models.DecimalField(max_digits=10, decimal_places=4)
    packing_height = models.DecimalField(max_digits=10, decimal_places=4)
    individual_packing_size = models.DecimalField(max_digits=10, decimal_places=4)    
    individual_packing_type = models.CharField(max_length=200)
    
    moq = models.IntegerField()

    total_stock = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.name


class ItemModelApplication(models.Model):
    item = models.ForeignKey('Item', on_delete=models.CASCADE)
    model_application = models.ForeignKey('ModelApplication', on_delete=models.CASCADE)
    note = models.CharField(max_length=100, blank=True)  # opcional: você pode adicionar campos extras
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    #def __str__(self):
    #    return self.item

