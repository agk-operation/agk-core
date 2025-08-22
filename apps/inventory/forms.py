from django import forms
from django.utils import timezone
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, HTML, Submit
from crispy_forms.bootstrap import PrependedText, AppendedText, FormActions
from django.forms.models import inlineformset_factory, BaseInlineFormSet
from django.db import models as djmodels
from . import models


class ItemForm(forms.ModelForm):
    class Meta:
        model = models.Item
        exclude = ['total_stock', 'created_at', 'updated_at', 'model_application', 
                   'net_weight', 'package_gross_weight', 'packing_lengh', 'packing_width', 
                   'packing_height', 'individual_packing_size', 'individual_packing_type',
        ]

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


class PackagingVersionForm(forms.ModelForm):
    class Meta:
        model = models.ItemPackagingVersion
        fields = models.ItemPackagingVersion.PACKAGING_FIELDS + ['valid_from','valid_to']
        widgets = {
            **{ fld: forms.NumberInput(attrs={'class':'form-control-sm','step':'0.0001'}) 
                for fld in models.ItemPackagingVersion.PACKAGING_FIELDS },
            'valid_from': forms.DateTimeInput(
                attrs={'type':'datetime-local','class':'form-control-sm'}
            ),
            'valid_to':   forms.DateTimeInput(
                attrs={'type':'datetime-local','class':'form-control-sm'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            # ===== Datas com ícone de calendário =====
            Row(
                Column('valid_from', css_class='col-md-6'),
                Column('valid_to', css_class='col-md-6'),
            ),
            HTML('<hr>'),
            # =====→ Dimensões (cm) =====
            HTML('<h5 class="mt-3">Dimensões (cm)</h5>'),
            Row(
                Column(
                    AppendedText('packing_lengh', 'cm'),
                    css_class='col-md-4'
                ),
                Column(
                    AppendedText('packing_width', 'cm'),
                    css_class='col-md-4'
                ),
                Column(
                    AppendedText('packing_height', 'cm'),
                    css_class='col-md-4'
                ),
            ),
            HTML('<hr>'),
            # =====→ Peso (kg) =====
            HTML('<h5 class="mt-3">Peso (kg)</h5>'),
            Row(
                Column(
                    AppendedText('net_weight', 'kg'),
                    css_class='col-md-6'
                ),
                Column(
                    AppendedText('package_gross_weight', 'kg'),
                    css_class='col-md-6'
                ),
            ),
            HTML('<hr>'),
            # =====→ Embalagem individual =====
            Row(
                Column(
                    AppendedText('individual_packing_size', 'cm³'),
                    css_class='col-md-6'
                ),
                Column(
                    'individual_packing_type',
                    css_class='col-md-6'
                ),
            ),
            HTML('<hr>'),
        )
        # Preenche valid_from no blank form (GET)
        if not self.is_bound and not self.instance.pk:
            now = timezone.localtime().replace(second=0, microsecond=0)
            self.fields['valid_from'].initial = now.strftime('%Y-%m-%dT%H:%M')


class PackagingVersionFormSet(BaseInlineFormSet):
    def _construct_form(self, i, **kwargs):
        form = super()._construct_form(i, **kwargs)
        # Se for extra (sem instance.pk) e SEM mudanças → pule validação
        if not form.instance.pk and not form.has_changed():
            form.empty_permitted = True
        return form

    def save_new(self, form, commit=True):
        """
        Garante valid_from mesmo se usuário não preencher.
        """
        obj = super().save_new(form, commit=False)
        if not form.cleaned_data.get('valid_from'):
            obj.valid_from = timezone.now()
        if commit:
            obj.save()
        return obj

ItemPackagingVersionFormSet = inlineformset_factory(
    models.Item,
    models.ItemPackagingVersion,
    form=PackagingVersionForm,
    formset=PackagingVersionFormSet,
    extra=1,
    can_delete=True,
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