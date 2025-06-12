from django import forms
from django.forms import inlineformset_factory
from .models import Order, OrderItem, OrderBatch, BatchItem


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['customer', 'exporter', 'company']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'exporter': forms.Select(attrs={'class': 'form-select'}),
            'company':  forms.Select(attrs={'class': 'form-select'}),
        }


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ('item', 'quantity')
        widgets = {
            'item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

OrderItemFormSet = inlineformset_factory(
    Order, OrderItem,
    form=OrderItemForm,
    extra=1, can_delete=True
)


class BatchItemForm(forms.ModelForm):
    class Meta:
        model = BatchItem
        fields = ('order_item', 'quantity')
        widgets = {
            'order_item': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

BatchItemFormSet = inlineformset_factory(
    OrderBatch, BatchItem,
    form=BatchItemForm,
    extra=1, can_delete=True
)

class OrderBatchForm(forms.ModelForm):
    class Meta:
        model = OrderBatch
        # “order” ficará oculto, “batch_code” e “status” apresentarão selects/text
        fields = ['order', 'batch_code', 'status']
        widgets = {
            'order': forms.HiddenInput(),        # já preenchemos na view
            'batch_code': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

BatchItemFormSet = inlineformset_factory(
    OrderBatch, BatchItem,
    fields=('order_item','quantity'),
    widgets={
      'order_item': forms.Select(attrs={'class': 'form-select'}),
      'quantity':   forms.NumberInput(attrs={'class':'form-control','min':1}),
    },
    extra=1, can_delete=True
)


class OrderItemsImportForm(forms.Form):
    file = forms.FileField(
        label="Arquivo (.xlsx ou .csv)",
        help_text="Faça upload de um .xlsx ou .csv com colunas: product, quantity, unit_price"
    )