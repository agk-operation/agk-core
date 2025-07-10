from django import forms
from django.db import models as djmodels
from . import models


class SalesRepresentativeForm(forms.ModelForm):
    class Meta:
        model = models.SalesRepresentative
        fields = ['name', 'email', 'phone', 'customers']
        widgets = {
            'customers': forms.Select(attrs={'class': 'form-select w-50'}),
        }

RELATED_MODELS = [
    'Company', 'Exporter', 
    'Customer', 'City', 'Port',
    'Province', 'Supplier', 'Currency', 'Project',
    
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