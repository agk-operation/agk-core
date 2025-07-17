from decimal import Decimal
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column

from django import forms
from .models import ProformaInvoice, PaymentCondition

class ProformaInvoiceForm(forms.ModelForm):
    class Meta:
        model = ProformaInvoice
        fields = ['usd_rmb', 'payment_terms', 'deposit_percentage']
        widgets = {
            'usd_rmb': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'payment_terms': forms.TextInput(attrs={'class': 'form-control'}),
            'deposit_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }



class PaymentConditionForm(forms.ModelForm):
    class Meta:
        model = PaymentCondition
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(Column('name', css_class='col-md-6')),
            Row(Column('description', css_class='col-md-12')),
        )