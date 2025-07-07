from django import forms
from django.db import models as djmodels
from . import models


class ItemForm(forms.ModelForm):
    class Meta:
        model = models.Item
        exclude = ['total_stock', 'created_at', 'updated_at', 'model_application']

        widgets = {
            'p_code': forms.TextInput(attrs={'class': 'form-control'}),
            's_code': forms.TextInput(attrs={'class': 'form-control'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'subcategory': forms.Select(attrs={'class': 'form-select'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'supplier_chain': forms.Select(attrs={'class': 'form-select'}),
            'chain': forms.Select(attrs={'class': 'form-select'}),
            'ncm': forms.Select(attrs={'class': 'form-select'}),
            'brand_manufacturer': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'net_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'package_gross_weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'packing_lengh': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'packing_width': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'packing_height': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'individual_packing_size': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'individual_packing_type': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'moq': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    
class ItemModelApplicationForm(forms.ModelForm):
    class Meta:
        model = models.ItemModelApplication
        fields = ['model_application']

        widgets = {
            'model_application' :  forms.Select(attrs={'class': 'form-select w-50'})
        }



ItemModelApplicationFormSet = forms.inlineformset_factory(
    models.Item,
    models.ItemModelApplication,
    form=ItemModelApplicationForm,
    fields=['model_application'],
    extra=1,
    can_delete=True
)


RELATED_MODELS = [
    'Category', 'Subcategory', 'Project',
    'SupplierChain', 'Chain', 'Ncm',
    'BrandManufacturer', 'ModelApplication', 'Currency'
]

for model_name in RELATED_MODELS:
    model = getattr(models, model_name)

    widgets = {}
    for field in model._meta.fields:
        if not field.editable or field.name == 'id':
            continue

        if isinstance(field, djmodels.TextField):
            widget = forms.Textarea(attrs={'class': 'form-control', 'rows': 3})

        elif isinstance(field, djmodels.CharField):
            widget = forms.TextInput(attrs={'class': 'form-control'})

        elif field.choices:
            widget = forms.Select(attrs={'class': 'form-select'})

        elif isinstance(field, (djmodels.ForeignKey, djmodels.OneToOneField)):
            widget = forms.Select(attrs={'class': 'form-select'})

        elif isinstance(field, djmodels.BooleanField):
            widget = forms.CheckboxInput(attrs={'class': 'form-check-input'})

        elif isinstance(field, djmodels.DecimalField):
            widget = forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})

        elif isinstance(field, djmodels.IntegerField):
            widget = forms.NumberInput(attrs={'class': 'form-control'})

        else:
            widget = forms.TextInput(attrs={'class': 'form-control'})

        widgets[field.name] = widget

    Meta = type('Meta', (), {
        'model': model,
        'fields': '__all__',
        'widgets': widgets,
    })

    form_class = type(f'{model_name}Form', (forms.ModelForm,), {'Meta': Meta})
    globals()[f'{model_name}Form'] = form_class